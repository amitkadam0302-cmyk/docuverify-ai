import { useEffect, useState } from "react";

import { Badge, Button, Card, Input, Toast } from "../components/ui.jsx";
import { createCandidate, listCandidates } from "../services/api.js";

export default function CandidateProfilePage() {
  const [candidates, setCandidates] = useState([]);
  const [form, setForm] = useState({ full_name: "", email: "", phone: "" });
  const [message, setMessage] = useState("");
  const load = () => listCandidates().then((response) => setCandidates(response.data)).catch(() => setCandidates([]));
  useEffect(() => { load(); }, []);
  async function submit(event) {
    event.preventDefault();
    await createCandidate(form).then(() => { setMessage("Candidate created."); setForm({ full_name: "", email: "", phone: "" }); load(); }).catch((error) => setMessage(error.userMessage || "Could not create candidate."));
  }
  return (
    <div className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
      <Card><Badge tone="info">Candidates</Badge><h1 className="mt-3 text-2xl font-semibold">Candidate Profiles</h1><form onSubmit={submit} className="mt-6 space-y-4"><Input label="Full name" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} required /><Input label="Email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required /><Input label="Phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /><Toast message={message} /><Button type="submit">Save</Button></form></Card>
      <Card><h2 className="text-lg font-semibold">Profiles</h2><div className="mt-4 space-y-3">{candidates.length ? candidates.map((candidate) => <div key={candidate.id} className="rounded-2xl bg-black/5 p-3 dark:bg-white/10"><p className="font-semibold">{candidate.full_name}</p><p className="text-sm text-[#6E6E73] dark:text-[#A1A1A6]">{candidate.email}</p></div>) : <p className="text-sm text-[#6E6E73] dark:text-[#A1A1A6]">No candidates yet.</p>}</div></Card>
    </div>
  );
}
