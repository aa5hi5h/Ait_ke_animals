export const precheckResponse = {
  findings: [
    {
      id: 'f1', field: 'date_of_birth', severity: 'high',
      values: [{ document: 'Aadhaar', value: '12/03/1998' }, { document: 'Income certificate', value: '12/03/1989' }],
      explanation: { en: 'The date of birth is different in these two documents. This can delay your application.', hi: 'इन दोनों दस्तावेज़ों में जन्म तिथि अलग है। इससे आपके आवेदन में देरी हो सकती है।', mr: 'या दोन्ही कागदपत्रांमधील जन्मतारीख वेगळी आहे. यामुळे तुमच्या अर्जाला विलंब होऊ शकतो.' },
      fix: { en: 'Please correct the date of birth on the Income certificate before submitting your application.', hi: 'आवेदन जमा करने से पहले आय प्रमाणपत्र में जन्म तिथि ठीक करवाएँ।', mr: 'अर्ज सादर करण्यापूर्वी उत्पन्न प्रमाणपत्रावरील जन्मतारीख दुरुस्त करून घ्या.' }
    },
    {
      id: 'f2', field: 'address', severity: 'medium',
      values: [{ document: 'Aadhaar', value: '14 Lake View Road, Pune' }, { document: 'Address proof', value: '41 Lake View Road, Pune' }],
      explanation: { en: 'The house number is different in your address documents. The application office may ask you to clarify this.', hi: 'आपके पते के दस्तावेज़ों में घर का नंबर अलग है। कार्यालय आपसे स्पष्टीकरण मांग सकता है।', mr: 'तुमच्या पत्त्याच्या कागदपत्रांमध्ये घर क्रमांक वेगळा आहे. कार्यालय स्पष्टीकरण मागू शकते.' },
      fix: { en: 'Use an address proof with house number 14, or have the address on the Aadhaar card corrected.', hi: 'घर नंबर 14 वाला पता प्रमाण उपयोग करें, या आधार कार्ड का पता ठीक करवाएँ।', mr: 'घर क्रमांक 14 असलेला पत्त्याचा पुरावा वापरा किंवा आधार कार्डवरील पत्ता दुरुस्त करून घ्या.' }
    }
  ],
  ignored: [
    { field: 'name', values: ['Sunita Devi', 'Sunita Dewi'], reason: { en: 'Spelling variation', hi: 'वर्तनी में अंतर', mr: 'शब्दलेखनातील फरक' } },
    { field: 'address', values: ['Lake View Road', 'Lakeview Rd.'], reason: { en: 'Common address abbreviation', hi: 'पते का सामान्य संक्षिप्त रूप', mr: 'पत्त्यातील सामान्य संक्षेप' } },
    { field: 'parent_name', values: ['Ramesh Kumar', 'Ramesh K.'], reason: { en: 'Name abbreviation', hi: 'नाम का संक्षिप्त रूप', mr: 'नावाचे संक्षिप्त रूप' } }
  ]
};

// Swap this function for POST /api/precheck multipart upload when FastAPI is ready.
export async function runPrecheck(files) {
  await new Promise(resolve => setTimeout(resolve, 2000));
  return precheckResponse;
}
