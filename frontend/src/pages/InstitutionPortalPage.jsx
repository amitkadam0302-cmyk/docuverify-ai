import { useEffect, useState } from "react";

import { Badge, Button, Card, Input, Select, Toast } from "../components/ui.jsx";
import { issueInstitutionCertificate, listInstitutionCertificates, revokeCertificate } from "../services/api.js";

export default function InstitutionPortalPage() {
  const [certificates, setCertificates] = useState([]);
  const [form, setForm] = useState({ student_name: "", course_name: "", issue_date: "", certificate_id: "", institution_id: 1 });
  const [message, setMessage] = useState("");

  const load = () => listInstitutionCertificates().then((response) => setCertificates(response.data)).catch(() => setCertificates([]));
  useEffect(() => { load(); }, []);

  async function submit(event) {
    event.preventDefault();
    setMessage("");
    try {
      await issueInstitutionCertificate(form);
      setMessage("Certificate issued.");
      setForm((current) => ({ ...current, student_name: "", course_name: "", certificate_id: "" }));
      load();
    } catch (requestError) {
      setMessage(requestError.userMessage || "Issue failed.");
    }
  }

  async function revoke(id) {
    await revokeCertificate(id).catch(() => null);
    load();
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[0.85fr_1.15fr]">
      <Card>
        <Badge tone="info">Institution</Badge><h1 className="mt-3 text-2xl font-semibold">Issue Certificate</h1>
        <form onSubmit={submit} className="mt-6 space-y-4">
          <Input label="Student name" value={form.student_name} onChange={(e) => setForm({ ...form, student_name: e.target.value })} required />
          <Input label="Course name" value={form.course_name} onChange={(e) => setForm({ ...form, course_name: e.target.value })} required />
          <Input label="Issue date" type="date" value={form.issue_date} onChange={(e) => setForm({ ...form, issue_date: e.target.value })} required />
          <Input label="Certificate ID" value={form.certificate_id} onChange={(e) => setForm({ ...form, certificate_id: e.target.value })} required />
          <Select label="Institution" value={form.institution_id} onChange={(e) => setForm({ ...form, institution_id: Number(e.target.value) })}><option value={1}>Institution #1</option></Select>
          <Toast message={message} />
          <Button type="submit">Issue Certificate</Button>
        </form>
      </Card>
      <Card>
        <h2 className="text-lg font-semibold">Certificate Records</h2>
        <div className="mt-4 space-y-3">
          {certificates.length ? certificates.map((item) => <div key={item.id} className="rounded-2xl bg-black/5 p-3 text-sm dark:bg-white/10"><div className="flex items-center justify-between gap-3"><p className="font-semibold">{item.student_name}</p><Badge tone={item.status === "valid" ? "success" : "danger"}>{item.status}</Badge></div><p className="text-[#6E6E73] dark:text-[#A1A1A6]">{item.course_name} · {item.certificate_id}</p><Button variant="secondary" className="mt-3" onClick={() => revoke(item.id)}>Revoke</Button></div>) : <p className="text-sm text-[#6E6E73] dark:text-[#A1A1A6]">No certificate records.</p>}
        </div>
      </Card>
    </div>
  );
}
