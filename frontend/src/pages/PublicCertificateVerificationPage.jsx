import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { Badge, Card, LoadingSpinner } from "../components/ui.jsx";
import { publicVerifyCertificate } from "../services/api.js";

export default function PublicCertificateVerificationPage() {
  const { certificateId } = useParams();
  const [record, setRecord] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => { publicVerifyCertificate(certificateId).then((response) => setRecord(response.data)).catch(() => setRecord(null)).finally(() => setLoading(false)); }, [certificateId]);
  if (loading) return <LoadingSpinner label="Checking certificate" />;
  return (
    <main className="grid min-h-screen place-items-center bg-[#F5F5F7] px-5 dark:bg-black">
      <Card className="w-full max-w-lg">
        <Badge tone={record?.status === "valid" ? "success" : "danger"}>{record?.status || "not found"}</Badge>
        <h1 className="mt-4 text-2xl font-semibold">Public Verification</h1>
        {record ? <div className="mt-5 space-y-2 text-sm"><p><strong>Student:</strong> {record.student_name}</p><p><strong>Course:</strong> {record.course_name}</p><p><strong>Institution:</strong> {record.institution_name}</p><p><strong>Issue date:</strong> {record.issue_date}</p></div> : <p className="mt-4 text-sm text-[#6E6E73] dark:text-[#A1A1A6]">Certificate record was not found.</p>}
      </Card>
    </main>
  );
}
