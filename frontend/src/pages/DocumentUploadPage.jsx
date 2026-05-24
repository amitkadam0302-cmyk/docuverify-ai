import { FileText, UploadCloud } from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Badge, Button, Card, Select, Toast } from "../components/ui.jsx";
import { runFullCheck, uploadDocument } from "../services/api.js";

const maxBytes = 10 * 1024 * 1024;
const allowedTypes = ["application/pdf", "image/jpeg", "image/png"];

export default function DocumentUploadPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [documentType, setDocumentType] = useState("certificate");
  const [progress, setProgress] = useState(0);
  const [uploaded, setUploaded] = useState(null);
  const [loading, setLoading] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState("");

  const fileError = useMemo(() => {
    if (!file) return "";
    if (file.size > maxBytes) return "File is too large.";
    if (!allowedTypes.includes(file.type)) return "Invalid file type.";
    return "";
  }, [file]);

  async function submit(event) {
    event.preventDefault();
    if (!file || fileError) return;
    setLoading(true);
    setError("");
    setProgress(5);
    try {
      const response = await uploadDocument({
        file,
        documentType,
        onUploadProgress: (event) => setProgress(Math.min(98, Math.round((event.loaded * 100) / (event.total || file.size || 1)))),
      });
      setUploaded(response.data);
      setProgress(100);
    } catch (requestError) {
      setError(requestError.userMessage || "Upload failed. Try again.");
      setProgress(0);
    } finally {
      setLoading(false);
    }
  }

  async function verify() {
    if (!uploaded) return;
    setVerifying(true);
    setError("");
    try {
      const response = await runFullCheck(uploaded.document_id);
      navigate(`/app/results/${uploaded.document_id}`, { state: { result: response.data } });
    } catch (requestError) {
      setError(requestError.userMessage || "Verification failed. Please retry.");
    } finally {
      setVerifying(false);
    }
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
      <Card>
        <Badge tone="info">Upload</Badge>
        <h1 className="mt-3 text-2xl font-semibold">Verify a document</h1>
        <p className="mt-2 text-sm text-[#6E6E73] dark:text-[#A1A1A6]">Documents are processed securely and used only for verification.</p>
        <form onSubmit={submit} className="mt-6 space-y-5">
          <Select label="Document type" value={documentType} onChange={(event) => setDocumentType(event.target.value)}>
            <option value="certificate">Certificate</option>
            <option value="resume">Resume</option>
            <option value="experience_letter">Experience Letter</option>
            <option value="marksheet">Marksheet</option>
            <option value="other">Other</option>
          </Select>
          <label className="grid cursor-pointer place-items-center rounded-apple border-2 border-dashed border-black/10 bg-white/50 p-8 text-center hover:border-[#007AFF]/40 dark:border-white/10 dark:bg-white/5">
            <UploadCloud className="h-9 w-9 text-[#007AFF]" />
            <span className="mt-3 text-sm font-semibold">{file ? file.name : "Upload Document"}</span>
            <span className="mt-1 text-xs text-[#6E6E73] dark:text-[#A1A1A6]">PDF, JPG, JPEG, or PNG</span>
            <input type="file" className="hidden" accept=".pdf,.jpg,.jpeg,.png" onChange={(event) => { setFile(event.target.files?.[0] || null); setUploaded(null); setError(""); }} />
          </label>
          {file && <FileDetails file={file} error={fileError} progress={progress} />}
          <Toast message={error || fileError} />
          <Button type="submit" loading={loading} disabled={!file || Boolean(fileError) || loading} icon={UploadCloud}>Upload</Button>
        </form>
      </Card>
      <Card>
        <h2 className="text-lg font-semibold">Next step</h2>
        {uploaded ? (
          <div className="mt-5 space-y-4">
            <div className="rounded-apple bg-[#34C759]/10 p-4">
              <p className="font-semibold">Ready to verify</p>
              <p className="mt-2 text-sm text-[#6E6E73] dark:text-[#A1A1A6]">Document ID: {uploaded.document_id}</p>
              <p className="mt-1 break-all font-mono text-xs text-[#6E6E73] dark:text-[#A1A1A6]">{uploaded.file_hash}</p>
            </div>
            <Button onClick={verify} loading={verifying} disabled={verifying}>Start Verification</Button>
          </div>
        ) : (
          <div className="mt-5 rounded-apple border border-dashed border-black/10 p-8 text-center dark:border-white/10">No document yet.</div>
        )}
      </Card>
    </div>
  );
}

function FileDetails({ file, error, progress }) {
  return (
    <div className="rounded-apple border border-black/10 bg-white/60 p-4 dark:border-white/10 dark:bg-white/5">
      <div className="flex items-center gap-3">
        <FileText className="h-5 w-5 text-[#007AFF]" />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold">{file.name}</p>
          <p className="text-xs text-[#6E6E73] dark:text-[#A1A1A6]">{file.type || "Unknown"} · {(file.size / 1024 / 1024).toFixed(2)} MB</p>
        </div>
        <Badge tone={error ? "danger" : "success"}>{error ? "Check file" : "Ready"}</Badge>
      </div>
      {progress > 0 && <div className="mt-3 h-2 overflow-hidden rounded-full bg-black/5 dark:bg-white/10"><div className="h-full rounded-full bg-[#007AFF]" style={{ width: `${progress}%` }} /></div>}
    </div>
  );
}
