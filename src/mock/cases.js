// In-memory case store for the reviewer dashboard.
//
// Shape is derived from the FastAPI detection models in
// backend/app/detect/types.py:
//   Finding        -> { field, decision, severity, reason, evidence, recommended_action }
//   FieldEvidence  -> { document_type, source_path, raw_value, normalized_value,
//                       source_confidence, source_bbox }
//   BundleDetectionResult -> { documents_processed, findings, summary, warnings }
//
// A "case" wraps that analysis with the reviewer-facing metadata the
// dashboard needs. When FastAPI lands, only src/api/cases.js changes.

export const APPLICATION_TYPES = [
  'Scholarship',
  'Ration card',
  'Passport',
  'Income certificate',
  'Address change',
  'Pension',
];

export const CASE_STATUSES = [
  'draft',
  'processing',
  'needs_review',
  'conflicts_found',
  'cleared',
];

const day = 24 * 60 * 60 * 1000;
const now = Date.now();

const finding = (overrides) => ({
  id: 'f1',
  field: 'date_of_birth',
  severity: 'HIGH',
  values: [],
  location: { document: '', field: '' },
  explanation: '',
  ...overrides,
});

const ignored = (overrides) => ({
  id: 'i1',
  field: 'name',
  values: ['', ''],
  reason: '',
  ...overrides,
});

export const seedCases = [
  {
    id: 'CASE-1042',
    applicantName: 'Sunita Devi',
    applicationType: 'Scholarship',
    notes: 'Applicant submitted three scans. Verify DOB before sanction.',
    documentCount: 3,
    createdAt: new Date(now - 2 * day).toISOString(),
    updatedAt: new Date(now - 4 * 60 * 60 * 1000).toISOString(),
    status: 'conflicts_found',
    decisions: { f1: 'pending', f2: 'pending' },
    findings: [
      finding({
        id: 'f1',
        field: 'date_of_birth',
        severity: 'HIGH',
        values: [
          { document: 'Aadhaar', value: '12/03/1998' },
          { document: 'Income certificate', value: '12/03/1989' },
        ],
        location: { document: 'Income certificate', field: 'Date of Birth' },
        explanation:
          'The date of birth differs between the two documents. Eligibility for this scheme depends on age.',
      }),
      finding({
        id: 'f2',
        field: 'address',
        severity: 'MEDIUM',
        values: [
          { document: 'Aadhaar', value: '14 Lake View Road, Pune' },
          { document: 'Address proof', value: '41 Lake View Road, Pune' },
        ],
        location: { document: 'Address proof', field: 'House number' },
        explanation: 'The house number is different in the two address documents.',
      }),
    ],
    ignored: [
      ignored({
        id: 'i1',
        field: 'name',
        values: ['Sunita Devi', 'Sunita Dewi'],
        reason: 'Spelling variation',
      }),
      ignored({
        id: 'i2',
        field: 'address',
        values: ['Lake View Road', 'Lakeview Rd.'],
        reason: 'Common address abbreviation',
      }),
      ignored({
        id: 'i3',
        field: 'parent_name',
        values: ['Ramesh Kumar', 'Ramesh K.'],
        reason: 'Name abbreviation',
      }),
    ],
  },
  {
    id: 'CASE-1041',
    applicantName: 'Ramesh Kumar Singh',
    applicationType: 'Ration card',
    notes: '',
    documentCount: 2,
    createdAt: new Date(now - 3 * day).toISOString(),
    updatedAt: new Date(now - 1 * day).toISOString(),
    status: 'needs_review',
    decisions: { f1: 'pending' },
    findings: [
      finding({
        id: 'f1',
        field: 'name',
        severity: 'MEDIUM',
        values: [
          { document: 'Aadhaar', value: 'Ramesh Kumar Singh' },
          { document: 'Application form', value: 'R. K. Singh' },
        ],
        location: { document: 'Application form', field: 'Applicant name' },
        explanation: 'The application form uses initials while the Aadhaar card spells the full name.',
      }),
    ],
    ignored: [
      ignored({
        id: 'i1',
        field: 'address',
        values: ['Plot 12, Sector 4', '12 Sec-4'],
        reason: 'Common address abbreviation',
      }),
    ],
  },
  {
    id: 'CASE-1040',
    applicantName: 'Aarti Patil',
    applicationType: 'Passport',
    notes: 'Police verification pending.',
    documentCount: 4,
    createdAt: new Date(now - 5 * day).toISOString(),
    updatedAt: new Date(now - 2 * day).toISOString(),
    status: 'cleared',
    decisions: { f1: 'accepted' },
    findings: [
      finding({
        id: 'f1',
        field: 'address',
        severity: 'LOW',
        values: [
          { document: 'Aadhaar', value: 'Flat 3B, Rose Apartments' },
          { document: 'Address proof', value: 'Unit 3B, Rose Apts' },
        ],
        location: { document: 'Address proof', field: 'Address' },
        explanation: 'Abbreviation differs but the address resolves to the same place.',
      }),
    ],
    ignored: [
      ignored({
        id: 'i1',
        field: 'name',
        values: ['Aarti Patil', 'Aarti Patil'],
        reason: 'Exact match after normalization',
      }),
    ],
  },
  {
    id: 'CASE-1039',
    applicantName: 'Mohammed Irfan',
    applicationType: 'Income certificate',
    notes: '',
    documentCount: 2,
    createdAt: new Date(now - 7 * day).toISOString(),
    updatedAt: new Date(now - 6 * day).toISOString(),
    status: 'draft',
    decisions: {},
    findings: [],
    ignored: [],
  },
  {
    id: 'CASE-1038',
    applicantName: 'Lakshmi Narayanan',
    applicationType: 'Pension',
    notes: 'Awaiting scanned pension book.',
    documentCount: 3,
    createdAt: new Date(now - 9 * day).toISOString(),
    updatedAt: new Date(now - 8 * day).toISOString(),
    status: 'processing',
    decisions: {},
    findings: [],
    ignored: [],
  },
  {
    id: 'CASE-1037',
    applicantName: 'Priya Sharma',
    applicationType: 'Address change',
    notes: '',
    documentCount: 3,
    createdAt: new Date(now - 11 * day).toISOString(),
    updatedAt: new Date(now - 10 * day).toISOString(),
    status: 'conflicts_found',
    decisions: { f1: 'pending' },
    findings: [
      finding({
        id: 'f1',
        field: 'date_of_birth',
        severity: 'HIGH',
        values: [
          { document: 'Aadhaar', value: '14/08/1994' },
          { document: 'Application form', value: '14/08/1996' },
        ],
        location: { document: 'Application form', field: 'Date of birth' },
        explanation: 'The date of birth differs by two years between the documents.',
      }),
    ],
    ignored: [],
  },
  {
    id: 'CASE-1036',
    applicantName: 'Sunita Devi',
    applicationType: 'Scholarship',
    notes: 'Second application for the same applicant.',
    documentCount: 2,
    createdAt: new Date(now - 13 * day).toISOString(),
    updatedAt: new Date(now - 12 * day).toISOString(),
    status: 'cleared',
    decisions: {},
    findings: [],
    ignored: [
      ignored({
        id: 'i1',
        field: 'name',
        values: ['Sunita Devi', 'Sunita Dewi'],
        reason: 'Spelling variation',
      }),
    ],
  },
  {
    id: 'CASE-1035',
    applicantName: 'Vikram Jadhav',
    applicationType: 'Ration card',
    notes: '',
    documentCount: 5,
    createdAt: new Date(now - 15 * day).toISOString(),
    updatedAt: new Date(now - 14 * day).toISOString(),
    status: 'needs_review',
    decisions: { f1: 'pending' },
    findings: [
      finding({
        id: 'f1',
        field: 'parent_name',
        severity: 'LOW',
        values: [
          { document: 'Aadhaar', value: 'Suresh Jadhav' },
          { document: 'Application form', value: 'S. Jadhav' },
        ],
        location: { document: 'Application form', field: "Father's name" },
        explanation: 'Father name is abbreviated on the application form.',
      }),
    ],
    ignored: [],
  },
  {
    id: 'CASE-1034',
    applicantName: 'Neha Kulkarni',
    applicationType: 'Passport',
    notes: '',
    documentCount: 3,
    createdAt: new Date(now - 18 * day).toISOString(),
    updatedAt: new Date(now - 17 * day).toISOString(),
    status: 'cleared',
    decisions: {},
    findings: [],
    ignored: [],
  },
  {
    id: 'CASE-1033',
    applicantName: 'Arjun Rao',
    applicationType: 'Income certificate',
    notes: 'Income figures checked against the certificate.',
    documentCount: 2,
    createdAt: new Date(now - 21 * day).toISOString(),
    updatedAt: new Date(now - 20 * day).toISOString(),
    status: 'cleared',
    decisions: { f1: 'dismissed' },
    findings: [
      finding({
        id: 'f1',
        field: 'income',
        severity: 'LOW',
        values: [
          { document: 'Income certificate', value: '₹ 96,000' },
          { document: 'Application form', value: '₹ 96000 per annum' },
        ],
        location: { document: 'Application form', field: 'Annual income' },
        explanation: 'Same amount written in a different format.',
      }),
    ],
    ignored: [],
  },
  {
    id: 'CASE-1032',
    applicantName: 'Deepa Shinde',
    applicationType: 'Address change',
    notes: '',
    documentCount: 2,
    createdAt: new Date(now - 25 * day).toISOString(),
    updatedAt: new Date(now - 24 * day).toISOString(),
    status: 'draft',
    decisions: {},
    findings: [],
    ignored: [],
  },
  {
    id: 'CASE-1031',
    applicantName: 'Imran Shaikh',
    applicationType: 'Pension',
    notes: '',
    documentCount: 4,
    createdAt: new Date(now - 30 * day).toISOString(),
    updatedAt: new Date(now - 29 * day).toISOString(),
    status: 'conflicts_found',
    decisions: { f1: 'pending' },
    findings: [
      finding({
        id: 'f1',
        field: 'date_of_birth',
        severity: 'MEDIUM',
        values: [
          { document: 'Aadhaar', value: '05/11/1962' },
          { document: 'Income certificate', value: '05/11/1961' },
        ],
        location: { document: 'Income certificate', field: 'Date of Birth' },
        explanation: 'The year of birth differs by one year across the two documents.',
      }),
    ],
    ignored: [],
  },
];
