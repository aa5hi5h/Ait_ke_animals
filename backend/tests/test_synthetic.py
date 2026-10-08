import json

from app.synthetic.generate import generate_bundles

CONFLICT_TYPES = {
    "dob_mismatch", "id_number_mismatch", "name_mismatch",
    "pincode_mismatch", "city_mismatch", "income_mismatch",
}
HARMLESS_TYPES = {
    "name_abbreviation", "name_spelling", "name_order_or_case",
    "address_abbreviation", "address_word_order", "date_format", "none",
}


def test_generate_bundles(tmp_path):
    counts = generate_bundles(count=6, seed=7, out_dir=tmp_path)

    label_files = sorted((tmp_path / "labels").glob("bundle_*.json"))
    assert len(label_files) == 6
    assert set(counts) <= CONFLICT_TYPES | HARMLESS_TYPES

    for label_file in label_files:
        bundle_id = label_file.stem

        # 3 PNGs per bundle
        pngs = sorted((tmp_path / "synthetic" / bundle_id).glob("*.png"))
        assert [p.name for p in pngs] == [
            "address_proof.png", "id_card.png", "income_certificate.png"]

        # valid JSON with the documented shape
        data = json.loads(label_file.read_text(encoding="utf-8"))
        assert data["bundle_id"] == bundle_id
        assert data["scenario"] in CONFLICT_TYPES | HARMLESS_TYPES
        assert set(data["documents"]) == {
            "id_card", "address_proof", "income_certificate"}

        # every rendered field has its value and pixel bbox
        for doc in data["documents"].values():
            assert doc["file"].endswith(".png")
            for field in doc["fields"].values():
                assert isinstance(field["value"], str) and field["value"]
                x1, y1, x2, y2 = field["bbox"]
                assert 0 <= x1 < x2 <= 1240
                assert 0 <= y1 < y2 <= 1748

        # conflicts are flagged true, harmless variants false
        for entry in data["injected"]:
            assert entry["type"] in CONFLICT_TYPES | HARMLESS_TYPES
            if entry["type"] in CONFLICT_TYPES:
                assert entry["is_conflict"] is True
                assert entry["severity"] in {"HIGH", "MEDIUM", "LOW"}
            else:
                assert entry["is_conflict"] is False
                assert entry["severity"] is None


def test_same_seed_is_reproducible(tmp_path):
    generate_bundles(count=3, seed=99, out_dir=tmp_path / "a")
    generate_bundles(count=3, seed=99, out_dir=tmp_path / "b")
    for name in ["bundle_0001.json", "bundle_0002.json", "bundle_0003.json"]:
        a = (tmp_path / "a" / "labels" / name).read_bytes()
        b = (tmp_path / "b" / "labels" / name).read_bytes()
        assert a == b
