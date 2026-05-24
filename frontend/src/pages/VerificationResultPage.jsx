import { ChevronDown, Download, RotateCcw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";

import { Badge, Button, Card, LoadingSpinner, RiskBadge, Toast } from "../components/ui.jsx";
import { downloadVerificationReport, getDocumentTimeline, getVerificationExplanations, getVerificationResult, runFullCheck } from "../services/api.js";

export default function VerificationResultPage() {
  const { documentId } = useParams();
  const location = useLocation();
  const [result, setResult] = useState(location.state?.result || null);
  const [timeline, setTimeline] = useState([]);
  const [explanations, setExplanations] = useState([]);
  const [loading, setLoading] = useState(!location.state?.result);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const [textOpen, setTextOpen] = useState(false);

  useEffect(() => {
    if (location.state?.result) return;
    getVerificationResult(documentId)
      .then((response) => setResult(response.data))
      .catch((requestError) => setError(requestError.userMessage || "Could not load result."))
      .finally(() => setLoading(false));
  }, [documentId, location.state]);

  useEffect(() => {
    getDocumentTimeline(documentId).then((response) => setTimeline(response.data)).catch(() => setTimeline([]));
  }, [documentId, result]);

  useEffect(() => {
    if (!result?.verification_id) return;
    getVerificationExplanations(result.verification_id).then((response) => setExplanations(response.data)).catch(() => setExplanations([]));
  }, [result]);

  async function startVerification() {
    setLoading(true);
    setError("");
    try {
      const response = await runFullCheck(documentId);
      setResult(response.data);
    } catch (requestError) {
      setError(requestError.userMessage || "Verification failed.");
    } finally {
      setLoading(false);
    }
  }

  async function downloadReport() {
    if (!result?.verification_id) return;
    try {
      const response = await downloadVerificationReport(result.verification_id);
      const url = URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = `docuverify-report-${result.verification_id}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setToast("Report downloaded.");
    } catch (requestError) {
      setToast(requestError.userMessage || "Download failed.");
    }
  }

  const checks = useMemo(() => buildChecks(result), [result]);
  if (loading) return <LoadingSpinner label="Loading result" />;
  if (error && !result) return <Card><Toast message={error} /><div className="mt-4"><Button onClick={startVerification}>Start Verification</Button></div></Card>;
  if (!result) return <Card><Toast message="Verification result not found." /><div className="mt-4"><Button onClick={startVerification}>Start Verification</Button></div></Card>;

  return (
    <div className="space-y-6">
      <Card>
        <div className="grid gap-6 lg:grid-cols-[auto_1fr] lg:items-center">
          <ScoreRing score={result.authenticity_score || 0} />
          <div>
            <Badge tone="violet">Verification Result</Badge>
            <h1 className="mt-3 text-2xl font-semibold">Review result</h1>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <Summary label="Risk Level" value={<RiskBadge riskLevel={result.risk_level} />} />
              <Summary label="Final Decision" value={(result.final_decision || "review required").replaceAll("_", " ")} />
              <Summary label="Document" value={`#${result.document_id}`} />
              <Summary label="Score" value={`${Math.round(result.authenticity_score || 0)}%`} />
            </div>
            <div className="mt-5 flex flex-col gap-3 sm:flex-row">
              <Button onClick={downloadReport} icon={Download}>Download Report</Button>
              <Link to="/app/upload"><Button variant="secondary" icon={RotateCcw}>Verify Document</Button></Link>
            </div>
            <div className="mt-3"><Toast message={toast} /></div>
          </div>
        </div>
      </Card>
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {checks.map((check) => <Card key={check.title}><Badge tone={check.tone}>{check.status}</Badge><h2 className="mt-3 font-semibold">{check.title}</h2><p className="mt-2 text-sm text-[#6E6E73] dark:text-[#A1A1A6]">{check.description}</p></Card>)}
      </section>
      <Card>
        <h2 className="text-lg font-semibold">Issues Found</h2>
        <div className="mt-4 grid gap-3">
          {(result.fraud_flags || []).length ? result.fraud_flags.map((flag, index) => <div key={`${flag.flag_type}-${index}`} className="rounded-2xl border border-black/10 p-3 text-sm dark:border-white/10"><Badge tone={severityTone(flag.severity)}>{flag.severity}</Badge><p className="mt-2 font-semibold">{flag.flag_type?.replaceAll("_", " ")}</p><p className="mt-1 text-[#6E6E73] dark:text-[#A1A1A6]">{flag.message}</p></div>) : <p className="text-sm text-[#6E6E73] dark:text-[#A1A1A6]">No fraud flags.</p>}
        </div>
      </Card>
      <Card>
        <h2 className="text-lg font-semibold">Explanation</h2>
        <p className="mt-3 text-sm leading-6 text-[#6E6E73] dark:text-[#A1A1A6]">{result.recommendation || "Verification complete."}</p>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {explanations.slice(0, 6).map((item, index) => <div key={index} className="rounded-2xl bg-black/5 p-3 text-sm dark:bg-white/10"><p className="font-semibold">{item.issue_title}</p><p className="mt-1 text-[#6E6E73] dark:text-[#A1A1A6]">{item.recommended_action}</p></div>)}
        </div>
      </Card>
      <Card>
        <button onClick={() => setTextOpen((current) => !current)} className="flex w-full items-center justify-between text-left"><h2 className="text-lg font-semibold">OCR text</h2><ChevronDown className={`h-5 w-5 transition ${textOpen ? "rotate-180" : ""}`} /></button>
        {textOpen && <pre className="mt-4 max-h-80 overflow-auto whitespace-pre-wrap rounded-2xl bg-black p-4 text-xs leading-5 text-white">{result.extracted_text || "No extracted text available."}</pre>}
      </Card>
      <Card>
        <h2 className="text-lg font-semibold">Timeline</h2>
        <div className="mt-4 grid gap-2">{timeline.length ? timeline.map((event) => <div key={event.id} className="rounded-2xl bg-black/5 p-3 text-sm dark:bg-white/10"><p className="font-semibold capitalize">{event.event_type?.replaceAll("_", " ")}</p><p className="text-[#6E6E73] dark:text-[#A1A1A6]">{event.event_message}</p></div>) : <p className="text-sm text-[#6E6E73] dark:text-[#A1A1A6]">No timeline yet.</p>}</div>
      </Card>
    </div>
  );
}

function ScoreRing({ score }) {
  const value = Math.round(score);
  return <div className="grid h-40 w-40 place-items-center rounded-full bg-[#007AFF]/10 text-center"><div><p className="text-4xl font-semibold">{value}%</p><p className="text-xs text-[#6E6E73] dark:text-[#A1A1A6]">Trust Score</p></div></div>;
}

function Summary({ label, value }) {
  return <div className="rounded-2xl bg-black/5 p-3 dark:bg-white/10"><p className="text-xs font-semibold uppercase text-[#6E6E73] dark:text-[#A1A1A6]">{label}</p><div className="mt-1 text-sm font-semibold capitalize">{value}</div></div>;
}

function buildChecks(result) {
  const details = result?.detailed_results || {};
  return [
    ["OCR", result?.extracted_text ? "Extracted" : "Unavailable"],
    ["Metadata", details.metadata?.metadata_status || "Not available"],
    ["QR Verification", details.qr?.qr_status || "Not available"],
    ["Hash Integrity", details.hash?.hash_status || "Not available"],
    ["Tamper Detection", details.tamper?.tampering_status || "Not available"],
    ["Institution Match", details.qr?.database_match ? "Matched" : "Not confirmed"],
  ].map(([title, description]) => ({ title, description, status: description, tone: description === "Matched" || description === "Extracted" || description === "matched" ? "success" : "info" }));
}

function severityTone(value) {
  return value === "high" || value === "critical" ? "danger" : value === "medium" ? "warning" : "info";
}
