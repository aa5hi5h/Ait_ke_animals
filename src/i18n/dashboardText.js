// Dashboard strings in English, Hindi and Marathi, matching the language
// toggle used elsewhere in Samanvay.

export const LANGS = [
  ['en', 'English'],
  ['hi', 'हिंदी'],
  ['mr', 'मराठी'],
];

export const dashboardText = {
  en: {
    brand: 'Samanvay',
    langLabel: 'Language',
    logout: 'Logout',

    // Dashboard header
    title: 'Your cases',
    subtitle: 'Open a case to review documents, findings and decisions.',
    newCase: '+ New case',

    // Summary cards
    totalCases: 'Total cases',
    needsReviewCard: 'Needs review',
    conflictsFoundCard: 'Conflicts found',
    clearedCard: 'Cleared',

    // Table
    caseId: 'Case ID',
    applicant: 'Applicant',
    applicationType: 'Application type',
    documents: 'Documents',
    created: 'Created',
    updated: 'Last updated',
    status: 'Status',
    conflicts: 'Conflicts',
    openCase: 'Open case',

    // Search / filter / paging
    searchPlaceholder: 'Search by case ID or applicant…',
    filterStatus: 'Filter by status',
    allStatuses: 'All statuses',
    loadMore: 'Load more',
    showing: 'Showing',
    of: 'of',
    cases: 'cases',

    // States
    loading: 'Loading cases…',
    emptyTitle: 'No cases yet',
    emptyText: 'Create your first case to upload documents and start a review.',
    errorTitle: 'Cases could not be loaded',
    retry: 'Retry',

    // Status labels
    draft: 'Draft',
    processing: 'Processing',
    needs_review: 'Needs review',
    conflicts_found: 'Conflicts found',
    cleared: 'Cleared',

    // New case
    newCaseTitle: 'New case',
    newCaseText: 'Add the applicant details. You can upload documents on the next screen.',
    applicantLabel: 'Applicant name',
    applicantPlaceholder: 'e.g. Sunita Devi',
    typeLabel: 'Application type',
    typePlaceholder: 'Select an application type',
    notesLabel: 'Notes (optional)',
    notesPlaceholder: 'Anything the next reviewer should know…',
    cancel: 'Cancel',
    create: 'Create case',
    creating: 'Creating…',
    required: 'Applicant name and application type are required.',

    // Case workspace
    backToDashboard: 'Back to dashboard',
    caseReport: 'Case report',
    documentsCompared: 'Documents compared',
    overallStatus: 'Overall status',
    harmlessIgnored: 'Harmless differences ignored',
    high: 'High',
    medium: 'Medium',
    low: 'Low',

    // Findings table
    findingsTable: 'Findings',
    field: 'Field',
    values: 'Conflicting values',
    severity: 'Severity',
    location: 'Location',
    explanation: 'Explanation',
    decision: 'Decision',
    noFindingsTitle: 'No analysis yet',
    noFindingsText: 'Run the document analysis above to populate this report.',

    // Decisions
    pending: 'Pending',
    accepted: 'Accepted',
    dismissed: 'Dismissed',
    decisionPending: 'Pending',
    decisionAccepted: 'Accepted',
    decisionDismissed: 'Dismissed',

    // Ignored
    ignoredTitle: 'Ignored as harmless',
    ignoredNote: 'These variations were matched automatically and are not conflicts.',
    noneIgnored: 'No harmless variations were found.',

    // Notes
    notesTitle: 'Reviewer notes',
    notesPlaceholder: 'Write your notes for this case…',
    saveNotes: 'Save notes',
    saving: 'Saving…',
    saved: 'Saved',

    // Actions
    markCleared: 'Mark case as cleared',
    blockedCleared: 'Resolve every pending High finding first',
    alreadyCleared: 'Case cleared',
    downloadReport: 'Download report (PDF)',
    analysisSection: 'Document analysis',
  },

  hi: {
    brand: 'समन्वय',
    langLabel: 'भाषा',
    logout: 'लॉग आउट',

    title: 'आपके मामले',
    subtitle: 'दस्तावेज़, निष्कर्ष और निर्णय देखने के लिए कोई मामला खोलें।',
    newCase: '+ नया मामला',

    totalCases: 'कुल मामले',
    needsReviewCard: 'समीक्षा आवश्यक',
    conflictsFoundCard: 'विरोधाभास मिले',
    clearedCard: 'पूर्ण',

    caseId: 'मामला आईडी',
    applicant: 'आवेदक',
    applicationType: 'आवेदन प्रकार',
    documents: 'दस्तावेज़',
    created: 'निर्माण तिथि',
    updated: 'अंतिम अद्यतन',
    status: 'स्थिति',
    conflicts: 'विरोधाभास',
    openCase: 'मामला खोलें',

    searchPlaceholder: 'मामला आईडी या आवेदक से खोजें…',
    filterStatus: 'स्थिति से फ़िल्टर करें',
    allStatuses: 'सभी स्थितियाँ',
    loadMore: 'और लोड करें',
    showing: 'दिखा रहे हैं',
    of: 'में से',
    cases: 'मामले',

    loading: 'मामले लोड हो रहे हैं…',
    emptyTitle: 'अभी कोई मामला नहीं',
    emptyText: 'दस्तावेज़ अपलोड करने और समीक्षा शुरू करने के लिए अपना पहला मामला बनाएँ।',
    errorTitle: 'मामले लोड नहीं हो सके',
    retry: 'पुनः प्रयास करें',

    draft: 'प्रारूप',
    processing: 'प्रसंस्करण जारी',
    needs_review: 'समीक्षा आवश्यक',
    conflicts_found: 'विरोधाभास मिले',
    cleared: 'पूर्ण',

    newCaseTitle: 'नया मामला',
    newCaseText: 'आवेदक विवरण जोड़ें। दस्तावेज़ अगली स्क्रीन पर अपलोड कर सकते हैं।',
    applicantLabel: 'आवेदक का नाम',
    applicantPlaceholder: 'जैसे सुनीता देवी',
    typeLabel: 'आवेदन प्रकार',
    typePlaceholder: 'आवेदन प्रकार चुनें',
    notesLabel: 'टिप्पणियाँ (वैकल्पिक)',
    notesPlaceholder: 'अगले समीक्षक के लिए कोई जानकारी…',
    cancel: 'रद्द करें',
    create: 'मामला बनाएँ',
    creating: 'बना रहे हैं…',
    required: 'आवेदक का नाम और आवेदन प्रकार आवश्यक हैं।',

    backToDashboard: 'डैशबोर्ड पर वापस',
    caseReport: 'मामला रिपोर्ट',
    documentsCompared: 'तुलना किए गए दस्तावेज़',
    overallStatus: 'समग्र स्थिति',
    harmlessIgnored: 'हानिरहित अंतर अनदेखे',
    high: 'उच्च',
    medium: 'मध्यम',
    low: 'कम',

    findingsTable: 'निष्कर्ष',
    field: 'फ़ील्ड',
    values: 'विरोधी मान',
    severity: 'गंभीरता',
    location: 'स्थान',
    explanation: 'व्याख्या',
    decision: 'निर्णय',
    noFindingsTitle: 'अभी विश्लेषण नहीं हुआ',
    noFindingsText: 'यह रिपोर्ट भरने के लिए ऊपर दस्तावेज़ विश्लेषण चलाएँ।',

    pending: 'लंबित',
    accepted: 'स्वीकृत',
    dismissed: 'खारिज',
    decisionPending: 'लंबित',
    decisionAccepted: 'स्वीकृत',
    decisionDismissed: 'खारिज',

    ignoredTitle: 'हानिरहित मानकर अनदेखा',
    ignoredNote: 'ये भिन्नताएँ स्वतः मिल गईं और विरोधाभास नहीं हैं।',
    noneIgnored: 'कोई हानिरहित भिन्नता नहीं मिली।',

    notesTitle: 'समीक्षक टिप्पणियाँ',
    notesPlaceholder: 'इस मामले के लिए अपनी टिप्पणियाँ लिखें…',
    saveNotes: 'टिप्पणियाँ सहेजें',
    saving: 'सहेज रहे हैं…',
    saved: 'सहेजा गया',

    markCleared: 'मामले को पूर्ण चिह्नित करें',
    blockedCleared: 'पहले सभी लंबित उच्च निष्कर्ष हल करें',
    alreadyCleared: 'मामला पूर्ण',
    downloadReport: 'रिपोर्ट डाउनलोड करें (PDF)',
    analysisSection: 'दस्तावेज़ विश्लेषण',
  },

  mr: {
    brand: 'समन्वय',
    langLabel: 'भाषा',
    logout: 'लॉग आउट',

    title: 'तुमचे प्रकरणे',
    subtitle: 'कागदपत्रे, निष्कर्ष आणि निर्णय पाहण्यासाठी प्रकरण उघडा.',
    newCase: '+ नवीन प्रकरण',

    totalCases: 'एकूण प्रकरणे',
    needsReviewCard: 'समीक्षा आवश्यक',
    conflictsFoundCard: 'विरोधाभास आढळले',
    clearedCard: 'पूर्ण',

    caseId: 'प्रकरण आयडी',
    applicant: 'अर्जदार',
    applicationType: 'अर्ज प्रकार',
    documents: 'कागदपत्रे',
    created: 'निर्मिती दिनांक',
    updated: 'शेवटचे अद्ययावत',
    status: 'स्थिती',
    conflicts: 'विरोधाभास',
    openCase: 'प्रकरण उघडा',

    searchPlaceholder: 'प्रकरण आयडी किंवा अर्जदाराने शोधा…',
    filterStatus: 'स्थितीनुसार फिल्टर',
    allStatuses: 'सर्व स्थित्या',
    loadMore: 'आणखी लोड करा',
    showing: 'दाखवत आहे',
    of: 'पैकी',
    cases: 'प्रकरणे',

    loading: 'प्रकरणे लोड होत आहेत…',
    emptyTitle: 'अद्याप प्रकरणे नाहीत',
    emptyText: 'कागदपत्रे अपलोड करण्यासाठी आणि समीक्षा सुरू करण्यासाठी पहिले प्रकरण तयार करा.',
    errorTitle: 'प्रकरणे लोड करता आली नाहीत',
    retry: 'पुन्हा प्रयत्न करा',

    draft: 'मसुदा',
    processing: 'प्रक्रिया सुरू',
    needs_review: 'समीक्षा आवश्यक',
    conflicts_found: 'विरोधाभास आढळले',
    cleared: 'पूर्ण',

    newCaseTitle: 'नवीन प्रकरण',
    newCaseText: 'अर्जदार तपशील जोडा. कागदपत्रे पुढच्या स्क्रीनवर अपलोड करता येतील.',
    applicantLabel: 'अर्जदाराचे नाव',
    applicantPlaceholder: 'उदा. सुनीता देवी',
    typeLabel: 'अर्ज प्रकार',
    typePlaceholder: 'अर्ज प्रकार निवडा',
    notesLabel: 'टीपा (पर्यायी)',
    notesPlaceholder: 'पुढील समीक्षकासाठी माहिती…',
    cancel: 'रद्द करा',
    create: 'प्रकरण तयार करा',
    creating: 'तयार करत आहोत…',
    required: 'अर्जदाराचे नाव आणि अर्ज प्रकार आवश्यक आहे.',

    backToDashboard: 'डॅशबोर्डवर परत',
    caseReport: 'प्रकरण अहवाल',
    documentsCompared: 'तुलना केलेली कागदपत्रे',
    overallStatus: 'एकूण स्थिती',
    harmlessIgnored: 'निरुपद्रवी फरक दुर्लक्षित',
    high: 'उच्च',
    medium: 'मध्यम',
    low: 'कमी',

    findingsTable: 'निष्कर्ष',
    field: 'क्षेत्र',
    values: 'विरोधी मूल्ये',
    severity: 'तीव्रता',
    location: 'स्थान',
    explanation: 'स्पष्टीकरण',
    decision: 'निर्णय',
    noFindingsTitle: 'अद्याप विश्लेषण झाले नाही',
    noFindingsText: 'हा अहवाल भरण्यासाठी वरील कागदपत्र विश्लेषण चालवा.',

    pending: 'प्रलंबित',
    accepted: 'स्वीकृत',
    dismissed: 'दुर्लक्षित',
    decisionPending: 'प्रलंबित',
    decisionAccepted: 'स्वीकृत',
    decisionDismissed: 'दुर्लक्षित',

    ignoredTitle: 'निरुपद्रवी मानून दुर्लक्षित',
    ignoredNote: 'हे फरक आपोआप जुळले व विरोधाभास नाहीत.',
    noneIgnored: 'कोणतेही निरुपद्रवी फरक आढळले नाहीत.',

    notesTitle: 'समीक्षक टीपा',
    notesPlaceholder: 'या प्रकरणासाठी तुमच्या टीपा लिहा…',
    saveNotes: 'टीपा जतन करा',
    saving: 'जतन करत आहोत…',
    saved: 'जतन केले',

    markCleared: 'प्रकरण पूर्ण म्हणून चिन्हांकित करा',
    blockedCleared: 'आधी सर्व प्रलंबित उच्च निष्कर्ष सोडवा',
    alreadyCleared: 'प्रकरण पूर्ण',
    downloadReport: 'अहवाल डाउनलोड करा (PDF)',
    analysisSection: 'कागदपत्र विश्लेषण',
  },
};

/** Locale for date formatting, matching the selected language. */
export const DATE_LOCALE = { en: 'en-IN', hi: 'hi-IN', mr: 'mr-IN' };

export function formatDate(iso, lang) {
  if (!iso) return '—';
  try {
    return new Intl.DateTimeFormat(DATE_LOCALE[lang] || 'en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    }).format(new Date(iso));
  } catch {
    return iso.slice(0, 10);
  }
}
