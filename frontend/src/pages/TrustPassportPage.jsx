import { useEffect, useState } from "react";

import { Badge, Button, Card, Select, Toast } from "../components/ui.jsx";
import { generateCandidatePassport, listCandidates } from "../services/api.js";

export default function TrustPassportPage() {
  const [candidates, setCandidates] = useState([]);
  const [candidateId, setCandidateId] = useState("");
  const [passport, setPassport] = useState(null);
  const [message, setMessage] = useState("");
  useEffect(() => { listCandidates().then((response) => setCandidates(response.data)).catch(() => setCandidates([])); }, []);
  async function generate() {
    await generateCandidatePassport(candidateId).then((response) => { setPassport(response.data); setMessage("Trust Passport generated."); }).catch((error) => setMessage(error.userMessage || "Could not generate Trust Passport."));
  }
  return (
    <div className="space-y-6">
      <Card><Badge tone="violet">Trust Passport</Badge><h1 className="mt-3 text-2xl font-semibold">Trust Passport</h1></Card>
      <Card className="max-w-2xl"><Select label="Candidate" value={candidateId} onChange={(e) => setCandidateId(e.target.value)}><option value="">Select candidate</option>{candidates.map((candidate) => <option key={candidate.id} value={candidate.id}>{candidate.full_name}</option>)}</Select><div className="mt-4"><Button onClick={generate} disabled={!candidateId}>Generate</Button></div><div className="mt-4"><Toast message={message} /></div>{passport && <div className="mt-6 rounded-apple bg-black/5 p-5 dark:bg-white/10"><p className="text-4xl font-semibold">{Math.round(passport.overall_score || 0)}%</p><p className="mt-1 text-sm text-[#6E6E73] dark:text-[#A1A1A6]">Overall Trust Score</p><p className="mt-4 text-sm">Risk level: {passport.risk_level}</p></div>}</Card>
    </div>
  );
}
