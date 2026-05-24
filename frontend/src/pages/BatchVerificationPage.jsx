import { useState } from "react";

import { Badge, Button, Card, Input, Select, Toast } from "../components/ui.jsx";
import { uploadBatch, verifyBatch } from "../services/api.js";

export default function BatchVerificationPage() {
  const [batchName, setBatchName] = useState("");
  const [documentType, setDocumentType] = useState("certificate");
  const [files, setFiles] = useState([]);
  const [batch, setBatch] = useState(null);
  const [message, setMessage] = useState("");

  async function upload(event) {
    event.preventDefault();
    setMessage("");
    try {
      const response = await uploadBatch({ batchName, documentType, files });
      setBatch(response.data);
      setMessage("Batch uploaded.");
    } catch (requestError) {
      setMessage(requestError.userMessage || "Batch upload failed.");
    }
  }

  async function verify() {
    if (!batch?.batch_id) return;
    const response = await verifyBatch(batch.batch_id).catch((error) => ({ error }));
    setMessage(response.error?.userMessage || "Batch verification complete.");
  }

  return (
    <div className="space-y-6">
      <Card><Badge tone="info">Batch</Badge><h1 className="mt-3 text-2xl font-semibold">Batch Verification</h1></Card>
      <Card>
        <form onSubmit={upload} className="grid gap-4 md:grid-cols-2">
          <Input label="Batch name" value={batchName} onChange={(e) => setBatchName(e.target.value)} required />
          <Select label="Document type" value={documentType} onChange={(e) => setDocumentType(e.target.value)}><option value="certificate">Certificate</option><option value="resume">Resume</option><option value="experience_letter">Experience Letter</option><option value="marksheet">Marksheet</option><option value="other">Other</option></Select>
          <input className="md:col-span-2" type="file" multiple accept=".pdf,.jpg,.jpeg,.png" onChange={(e) => setFiles(Array.from(e.target.files || []))} />
          <div className="flex gap-3 md:col-span-2"><Button type="submit" disabled={!files.length}>Upload</Button><Button type="button" variant="secondary" disabled={!batch} onClick={verify}>Start Verification</Button></div>
        </form>
        <div className="mt-4"><Toast message={message} /></div>
      </Card>
    </div>
  );
}
