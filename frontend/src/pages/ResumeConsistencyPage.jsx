import { useEffect, useState } from "react";

import { Badge, Button, Card, Select, Toast } from "../components/ui.jsx";
import { getMyDocuments, runResumeConsistency } from "../services/api.js";

export default function ResumeConsistencyPage() {
  const [documents, setDocuments] = useState([]);
  const [resumeId, setResumeId] = useState("");
  const [result, setResult] = useState(null);
  const [message, setMessage] = useState("");
  useEffect(() => { getMyDocuments().then((response) => setDocuments(response.data)).catch(() => setDocuments([])); }, []);
  async function run() {
    const supporting = documents.filter((item) => String(item.id) !== String(resumeId)).map((item) => item.id);
    await runResumeConsistency({ resume_document_id: Number(resumeId), supporting_document_ids: supporting }).then((response) => setResult(response.data)).catch((error) => setMessage(error.userMessage || "Consistency check failed."));
  }
  return (
    <div className="space-y-6">
      <Card><Badge tone="info">Resume</Badge><h1 className="mt-3 text-2xl font-semibold">Resume Consistency</h1></Card>
      <Card className="max-w-2xl"><Select label="Resume document" value={resumeId} onChange={(e) => setResumeId(e.target.value)}><option value="">Select resume</option>{documents.map((document) => <option key={document.id} value={document.id}>{document.original_filename}</option>)}</Select><div className="mt-4"><Button onClick={run} disabled={!resumeId}>Run Check</Button></div><Toast message={message} />{result && <div className="mt-5 rounded-apple bg-black/5 p-4 dark:bg-white/10"><p className="text-3xl font-semibold">{Math.round(result.consistency_score)}%</p><p className="text-sm text-[#6E6E73] dark:text-[#A1A1A6]">{result.recommendation}</p></div>}</Card>
    </div>
  );
}
