"""Synthetic document bundle generator (Step 2: setup only).

Each bundle is one fake citizen with three generic documents, rendered as
PNG images that carry a visible "SPECIMEN - SYNTHETIC" watermark, plus a
ground-truth label JSON. No real identities, no official designs.
"""

from __future__ import annotations

import argparse
import json
import random
import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from faker import Faker
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------- page layout
PAGE_W, PAGE_H = 1240, 1748          # A5-ish at ~212 dpi
MARGIN = 80
LABEL_W = 360
VALUE_X = MARGIN + LABEL_W
RIGHT_EDGE = PAGE_W - MARGIN
BODY_TOP = 350
VALUE_SIZE = 42                      # large enough for Tesseract
LABEL_SIZE = 34
LINE_H = 58                          # height of one value line
ROW_GAP = 46                         # gap between rows
WATERMARK = "SPECIMEN - SYNTHETIC"

BLACK = (20, 20, 20)
GRAY = (120, 120, 120)
LABEL_GRAY = (95, 95, 95)
RED = (185, 30, 30)

TITLE = {
    "id_card": "IDENTITY DOCUMENT",
    "address_proof": "UTILITY BILL",
    "income_certificate": "INCOME CERTIFICATE",
}
DOC_TYPES = list(TITLE)

# fields rendered as rows, in order (address parts live inside "address")
DOC_FIELDS = {
    "id_card": ["name", "father_name", "dob", "gender", "id_number", "address"],
    "address_proof": ["name", "address", "bill_date", "account_number"],
    "income_certificate": [
        "name", "father_name", "dob", "id_number",
        "annual_income", "issue_date", "address",
    ],
}
ADDRESS_PARTS = ["house_no", "locality", "city", "state", "pincode"]

FIELD_LABEL = {
    "name": "FULL NAME",
    "father_name": "FATHER'S NAME",
    "dob": "DATE OF BIRTH",
    "gender": "GENDER",
    "id_number": "ID NUMBER",
    "address": "ADDRESS",
    "bill_date": "BILL DATE",
    "account_number": "ACCOUNT NUMBER",
    "annual_income": "ANNUAL INCOME",
    "issue_date": "ISSUE DATE",
}
LABEL_OVERRIDE = {("address_proof", "name"): "NAME"}

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_CITIES = ["Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Ahmedabad", "Jaipur",
           "Lucknow", "Kochi", "Indore", "Patna", "Surat", "Nagpur",
           "Bhopal", "Chandigarh"]

# harmless-variant word maps
_ABBREV_NAME = {"Mohammad": "Mohd.", "Mohammed": "Mohd.", "Muhammad": "Mohd.",
                "Kumar": "Kr.", "Kumari": "Kr."}
_ABBREV_ADDR = ((r"\bRoad\b", "Rd"), (r"\bStreet\b", "St"), (r"\bNear\b", "Nr"))


# ------------------------------------------------------------------- helpers
def _inr(amount: int) -> str:
    """Indian digit grouping: 450000 -> '4,50,000'."""
    s = str(amount)
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join(groups) + "," + tail


def _group_id(digits: str) -> str:
    """12 digits -> 'XXXX XXXX XXXX'."""
    return f"{digits[0:4]} {digits[4:8]} {digits[8:12]}"


def _compose(f: dict) -> str:
    """Compose the address string from its parts (honouring __order)."""
    order = f.get("__order", ADDRESS_PARTS)
    out = []
    for i, part in enumerate(order):
        if i:
            out.append(", ")
        out.append(f[part])
    return "".join(out)


def _refresh_address(f: dict) -> None:
    f["address"] = _compose(f)


def _doc_has(doc: str, field: str) -> bool:
    if field in DOC_FIELDS[doc]:
        return True
    return "address" in DOC_FIELDS[doc] and field in ADDRESS_PARTS


# ----------------------------------------------------------------- scenarios
@dataclass(frozen=True)
class Scenario:
    type: str
    field: str | None        # None -> clean bundle
    is_conflict: bool
    severity: str | None     # conflicts only; harmless variants are None
    apply: Callable | None   # (scenario, values, rng, fake) -> entry or None


def _pair(s: Scenario, values: dict, rng: random.Random) -> tuple[str, str]:
    """Pick a target document to mutate plus a reference document."""
    docs = [d for d in DOC_TYPES if _doc_has(d, s.field)]
    target = rng.choice(docs)
    other = next(d for d in docs if d != target)
    return target, other


def _entry(s: Scenario, docs_pair: tuple, values: dict) -> dict:
    docs = [d for d in DOC_TYPES if d in docs_pair]
    return {
        "type": s.type,
        "field": s.field,
        "is_conflict": s.is_conflict,
        "severity": s.severity,
        "docs": docs,
        "values": {d: values[d][s.field] for d in docs},
    }


def _apply_dob(s, values, rng, fake):
    """Different month or day in one document (HIGH)."""
    target, other = _pair(s, values, rng)
    d = datetime.strptime(values[target]["dob"], "%d/%m/%Y").date()
    if rng.random() < 0.5:                       # change the month
        month = rng.choice([m for m in range(1, 13) if m != d.month])
        day = d.day if d.day <= 28 else 15
        new = date(d.year, month, day)
    else:                                        # change the day
        day = rng.choice([x for x in range(1, 29) if x != d.day])
        new = date(d.year, d.month, day)
    values[target]["dob"] = new.strftime("%d/%m/%Y")
    return _entry(s, (target, other), values)


def _apply_id_number(s, values, rng, fake):
    """Exactly one digit of the ID number differs (HIGH)."""
    target, other = _pair(s, values, rng)
    digits = [c for c in values[target]["id_number"] if c.isdigit()]
    i = rng.randrange(12)
    digits[i] = str((int(digits[i]) + rng.randint(1, 9)) % 10)   # never equal
    values[target]["id_number"] = _group_id("".join(digits))
    return _entry(s, (target, other), values)


def _apply_name(s, values, rng, fake):
    """A genuinely different name in one document (MEDIUM)."""
    target, other = _pair(s, values, rng)
    new = fake.name()
    while new == values[target]["name"]:
        new = fake.name()
    values[target]["name"] = new
    return _entry(s, (target, other), values)


def _apply_pincode(s, values, rng, fake):
    """Different 6-digit pincode in one document (MEDIUM)."""
    target, other = _pair(s, values, rng)
    new = str(rng.randint(100000, 999999))
    while new == values[target]["pincode"]:
        new = str(rng.randint(100000, 999999))
    values[target]["pincode"] = new
    _refresh_address(values[target])
    return _entry(s, (target, other), values)


def _apply_city(s, values, rng, fake):
    """Different city in one document (MEDIUM)."""
    target, other = _pair(s, values, rng)
    choices = [c for c in _CITIES if c != values[target]["city"]]
    values[target]["city"] = rng.choice(choices)
    _refresh_address(values[target])
    return _entry(s, (target, other), values)


def _apply_income(s, values, rng, fake):
    """Different annual income (LOW). Only possible if income is shown twice."""
    docs = [d for d in DOC_TYPES if _doc_has(d, s.field)]
    if len(docs) < 2:          # annual income appears once -> never selected
        return None
    target, other = _pair(s, values, rng)
    old = values[target]["annual_income"]
    new = old
    while new == old:
        new = f"Rs. {_inr(rng.randrange(150, 1201) * 1000)}"
    values[target]["annual_income"] = new
    return _entry(s, (target, other), values)


def _apply_name_abbr(s, values, rng, fake):
    """Mohammad -> Mohd, Kumar -> Kr. (harmless)."""
    target, other = _pair(s, values, rng)
    tokens = values[target]["name"].split()
    out = [_ABBREV_NAME.get(t, t) for t in tokens]
    if out == tokens:          # no known token: abbreviate the given name
        out[0] = tokens[0][0] + "."
    values[target]["name"] = " ".join(out)
    return _entry(s, (target, other), values)


def _spelling_variant(word: str) -> str:
    if len(word) > 2 and word.endswith("h"):   # Sharma -> Sarma, Singh -> Sing
        return word[:-1]
    return word + word[-1]                     # e.g. Verma -> Vermaa


def _apply_name_spelling(s, values, rng, fake):
    """Surname spelt differently (harmless)."""
    target, other = _pair(s, values, rng)
    tokens = values[target]["name"].split()
    tokens[-1] = _spelling_variant(tokens[-1])
    values[target]["name"] = " ".join(tokens)
    return _entry(s, (target, other), values)


def _apply_name_order(s, values, rng, fake):
    """SURNAME FIRSTNAME in uppercase (harmless)."""
    target, other = _pair(s, values, rng)
    tokens = values[target]["name"].split()
    if len(tokens) >= 2:
        values[target]["name"] = " ".join(
            [tokens[-1].upper()] + [t.upper() for t in tokens[:-1]])
    else:
        values[target]["name"] = values[target]["name"].upper()
    return _entry(s, (target, other), values)


def _apply_addr_abbr(s, values, rng, fake):
    """Road -> Rd, Street -> St, Near -> Nr (harmless)."""
    target, other = _pair(s, values, rng)
    for part in ADDRESS_PARTS:
        text = values[target][part]
        for pattern, repl in _ABBREV_ADDR:
            text = re.sub(pattern, repl, text)
        values[target][part] = text
    _refresh_address(values[target])
    return _entry(s, (target, other), values)


def _apply_addr_order(s, values, rng, fake):
    """Same address parts in a different order (harmless)."""
    target, other = _pair(s, values, rng)
    head = ADDRESS_PARTS[:-1]
    new_head = rng.sample(head, len(head))
    while new_head == head:     # make sure the order really changes
        new_head = rng.sample(head, len(head))
    values[target]["__order"] = new_head + [ADDRESS_PARTS[-1]]
    _refresh_address(values[target])
    return _entry(s, (target, other), values)


def _apply_date_format(s, values, rng, fake):
    """12/03/2001 vs 12-Mar-2001 (harmless)."""
    target, other = _pair(s, values, rng)
    d = datetime.strptime(values[target]["dob"], "%d/%m/%Y").date()
    values[target]["dob"] = f"{d.day:02d}-{_MONTHS[d.month - 1]}-{d.year}"
    return _entry(s, (target, other), values)


SCENARIOS = [
    # real conflicts
    Scenario("dob_mismatch", "dob", True, "HIGH", _apply_dob),
    Scenario("id_number_mismatch", "id_number", True, "HIGH", _apply_id_number),
    Scenario("name_mismatch", "name", True, "MEDIUM", _apply_name),
    Scenario("pincode_mismatch", "pincode", True, "MEDIUM", _apply_pincode),
    Scenario("city_mismatch", "city", True, "MEDIUM", _apply_city),
    Scenario("income_mismatch", "annual_income", True, "LOW", _apply_income),
    # harmless variants
    Scenario("name_abbreviation", "name", False, None, _apply_name_abbr),
    Scenario("name_spelling", "name", False, None, _apply_name_spelling),
    Scenario("name_order_or_case", "name", False, None, _apply_name_order),
    Scenario("address_abbreviation", "address", False, None, _apply_addr_abbr),
    Scenario("address_word_order", "address", False, None, _apply_addr_order),
    Scenario("date_format", "dob", False, None, _apply_date_format),
    # clean bundle with no differences
    Scenario("none", None, False, None, None),
]
_BY_TYPE = {s.type: s for s in SCENARIOS}


def _available_scenarios() -> list[Scenario]:
    """Scenarios whose field is shown on >= 2 documents, plus 'none'.

    annual_income appears only on the income certificate, so income_mismatch
    is skipped (see the task spec: skip if income appears in one place only).
    """
    pool = []
    for s in SCENARIOS:
        if s.field is None or s.apply is None:
            pool.append(s)
        elif sum(_doc_has(d, s.field) for d in DOC_TYPES) >= 2:
            pool.append(s)
    return pool


def _balanced_sequence(rng: random.Random, count: int) -> list[Scenario]:
    """Shuffled blocks of the pool so scenario counts stay balanced."""
    pool = _available_scenarios()
    seq: list[Scenario] = []
    while len(seq) < count:
        block = list(pool)
        rng.shuffle(block)
        seq.extend(block)
    return seq[:count]


# ------------------------------------------------------------- citizen values
def _make_citizen(rng: random.Random, fake: Faker) -> dict[str, dict]:
    """Field values for the three documents of one fake citizen."""
    gender = rng.choice(["Male", "Female"])
    name = fake.name_female() if gender == "Female" else fake.name_male()
    father = fake.name_male()
    dob = fake.date_of_birth(minimum_age=21, maximum_age=65)
    id_number = _group_id("".join(str(rng.randrange(10)) for _ in range(12)))

    locality = fake.street_name()
    if not re.search(r"\b(Road|Street|Near)\b", locality):
        locality = f"{locality} {rng.choice(['Road', 'Street'])}"
    addr = {
        "house_no": fake.building_number(),
        "locality": locality,
        "city": fake.city(),
        "state": fake.state(),
        "pincode": fake.postcode(),
    }
    if not (addr["pincode"].isdigit() and len(addr["pincode"]) == 6):
        addr["pincode"] = "".join(str(rng.randrange(10)) for _ in range(6))
    addr["address"] = _compose(addr)

    ref = date(2025, 1, 1)      # fixed reference keeps dates reproducible
    bill_date = (ref + timedelta(days=rng.randrange(0, 300))).strftime("%d/%m/%Y")
    issue_date = (ref + timedelta(days=rng.randrange(0, 300))).strftime("%d/%m/%Y")
    income = f"Rs. {_inr(rng.randrange(150, 1201) * 1000)}"

    return {
        "id_card": {
            "name": name, "father_name": father,
            "dob": dob.strftime("%d/%m/%Y"), "gender": gender,
            "id_number": id_number, **addr,
        },
        "address_proof": {
            "name": name, **addr,
            "bill_date": bill_date,
            "account_number": "".join(str(rng.randrange(10)) for _ in range(11)),
        },
        "income_certificate": {
            "name": name, "father_name": father,
            "dob": dob.strftime("%d/%m/%Y"), "id_number": id_number,
            "annual_income": income, "issue_date": issue_date, **addr,
        },
    }


# ------------------------------------------------------------------ rendering
_FONT_CACHE: dict[tuple[int, bool], ImageFont.ImageFont] = {}
_FONT_FILES = {
    True: ["C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/segoeuib.ttf",
           "C:/Windows/Fonts/DejaVuSans-Bold.ttf"],
    False: ["C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/DejaVuSans.ttf"],
}


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    key = (size, bold)
    if key not in _FONT_CACHE:
        loaded = None
        for path in _FONT_FILES[bold]:
            if Path(path).exists():
                loaded = ImageFont.truetype(path, size)
                break
        _FONT_CACHE[key] = loaded or ImageFont.load_default(size)
    return _FONT_CACHE[key]


def _center(draw: ImageDraw.ImageDraw, text: str, font, fill, y: int) -> None:
    w = draw.textlength(text, font=font)
    draw.text(((PAGE_W - w) / 2, y), text, font=font, fill=fill)


def _label_for(doc: str, field: str) -> str:
    return LABEL_OVERRIDE.get((doc, field), FIELD_LABEL[field])


def _address_segments(f: dict) -> list[tuple]:
    order = f.get("__order", ADDRESS_PARTS)
    segs: list[tuple] = []
    for i, part in enumerate(order):
        if i:
            segs.append((None, ", "))
        segs.append((part, f[part]))
    return segs


def _rows(doc: str, f: dict) -> list[tuple]:
    """(label, segments, whole_field, whole_value) rows for one document."""
    rows = []
    for name in DOC_FIELDS[doc]:
        if name == "address":
            rows.append((_label_for(doc, name), _address_segments(f),
                         "address", f["address"]))
        else:
            rows.append((_label_for(doc, name), [(name, f[name])], name, f[name]))
    return rows


def _draw_row(draw, label: str, segments: list[tuple], y: int):
    """Draw one label/value row, wrapping long values; returns new y, boxes,
    and the union bbox of the whole value."""
    vf = _font(VALUE_SIZE)
    draw.text((MARGIN, y + 4), label, font=_font(LABEL_SIZE, True),
              fill=LABEL_GRAY)
    x, ly = float(VALUE_X), y
    pending = ""
    boxes: dict[str, dict] = {}
    union = None
    for name, text in segments:
        if name is None:                     # separator, held until a value
            pending += text
            continue
        needed = draw.textlength(pending + text, font=vf)
        if x + needed > RIGHT_EDGE and x > VALUE_X:   # wrap at segment edge
            ly += LINE_H
            x, pending = float(VALUE_X), ""
        if pending:
            draw.text((x, ly), pending, font=vf, fill=BLACK)
            x += draw.textlength(pending, font=vf)
            pending = ""
        box = [int(round(v)) for v in draw.textbbox((x, ly), text, font=vf)]
        draw.text((x, ly), text, font=vf, fill=BLACK)
        boxes[name] = {"value": text, "bbox": box}
        if union is None:
            union = list(box)
        else:
            union = [min(union[0], box[0]), min(union[1], box[1]),
                     max(union[2], box[2]), max(union[3], box[3])]
        x += draw.textlength(text, font=vf)
    return ly + LINE_H + ROW_GAP, boxes, union


def _watermark(img: Image.Image) -> None:
    """Big diagonal SPECIMEN - SYNTHETIC watermark."""
    layer = Image.new("RGBA", (3200, 520), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((1600, 260), WATERMARK, font=_font(115, True),
                               fill=(140, 140, 140, 70), anchor="mm")
    layer = layer.rotate(38, expand=True, resample=Image.BICUBIC)
    if layer.width < PAGE_W or layer.height < PAGE_H:      # keep crop safe
        pad = Image.new("RGBA",
                        (max(layer.width, PAGE_W), max(layer.height, PAGE_H)),
                        (0, 0, 0, 0))
        pad.alpha_composite(layer, ((pad.width - layer.width) // 2,
                                    (pad.height - layer.height) // 2))
        layer = pad
    ox, oy = (layer.width - PAGE_W) // 2, (layer.height - PAGE_H) // 2
    img.alpha_composite(layer.crop((ox, oy, ox + PAGE_W, oy + PAGE_H)))


def render_document(doc: str, fields: dict, path: Path) -> dict:
    """Draw one document to `path`; return {field: {value, bbox}}."""
    img = Image.new("RGBA", (PAGE_W, PAGE_H), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)

    _center(draw, WATERMARK, _font(46, True), RED, 44)          # top banner
    _center(draw, TITLE[doc], _font(54, True), BLACK, 140)
    _center(draw, "Generic sample layout - synthetic data", _font(28), GRAY, 226)
    draw.line([(MARGIN, 286), (RIGHT_EDGE, 286)], fill=(205, 205, 205), width=3)

    boxes: dict[str, dict] = {}
    y = BODY_TOP
    for label, segments, whole, whole_value in _rows(doc, fields):
        y, seg_boxes, union = _draw_row(draw, label, segments, y)
        boxes.update(seg_boxes)
        if whole is not None and whole not in seg_boxes:
            boxes[whole] = {"value": whole_value, "bbox": union}

    _watermark(img)
    _center(draw, WATERMARK, _font(40, True), RED, PAGE_H - 150)  # bottom banner
    _center(draw, "All data is synthetic - generated for automated testing.",
            _font(26), GRAY, PAGE_H - 88)

    img.convert("RGB").save(path, "PNG", dpi=(212, 212))
    return boxes


# ---------------------------------------------------------------- generation
def generate_bundles(count: int = 40, seed: int = 42,
                     out_dir: str | Path = "data") -> dict[str, int]:
    """Generate `count` bundles under out_dir/synthetic and out_dir/labels.

    Returns {scenario_type: number_of_bundles}.
    """
    rng = random.Random(seed)
    fake = Faker("en_IN")
    fake.seed_instance(seed)

    out = Path(out_dir)
    doc_dir = out / "synthetic"
    label_dir = out / "labels"
    doc_dir.mkdir(parents=True, exist_ok=True)
    label_dir.mkdir(parents=True, exist_ok=True)

    sequence = _balanced_sequence(rng, count)
    counts: Counter = Counter()

    for index, scenario in enumerate(sequence, start=1):
        bundle_id = f"bundle_{index:04d}"
        values = _make_citizen(rng, fake)

        injected = []
        if scenario.apply is not None:
            entry = scenario.apply(scenario, values, rng, fake)
            if entry is not None:
                injected.append(entry)

        bundle_dir = doc_dir / bundle_id
        bundle_dir.mkdir(parents=True, exist_ok=True)
        documents = {}
        for doc in DOC_TYPES:
            fields = render_document(doc, values[doc], bundle_dir / f"{doc}.png")
            documents[doc] = {"file": f"{doc}.png", "fields": fields}

        label = {
            "bundle_id": bundle_id,
            "scenario": scenario.type,
            "documents": documents,
            "injected": injected,
        }
        (label_dir / f"{bundle_id}.json").write_text(
            json.dumps(label, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")
        counts[scenario.type] += 1

    return dict(counts)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic document bundles (all data is fake).")
    parser.add_argument("--count", type=int, default=40,
                        help="number of bundles (default: 40)")
    parser.add_argument("--seed", type=int, default=42,
                        help="random seed for reproducible output (default: 42)")
    parser.add_argument("--out", type=str, default="data",
                        help="output directory containing synthetic/ and labels/ "
                             "(default: data)")
    args = parser.parse_args(argv)

    counts = generate_bundles(count=args.count, seed=args.seed, out_dir=args.out)
    print(f"Generated {args.count} bundles (seed={args.seed}) in "
          f"{Path(args.out).resolve()}")
    for name in sorted(counts):
        print(f"  {name}: {counts[name]}")


if __name__ == "__main__":
    main()
