import { ArrowRight, FileText } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Badge, Button, Card, EmptyState, LoadingSpinner } from "../components/ui.jsx";
import { getMyDocuments } from "../services/api.js";

export default function VerificationHistoryPage() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMyDocuments().then((response) => setDocuments(response.data)).catch(() => setDocuments([])).finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner label="Loading results" />;

  return (
    <div className="space-y-6">
      <Card><Badge tone="info">Results</Badge><h1 className="mt-3 text-2xl font-semibold">Verification Results</h1></Card>
      <Card className="p-0">
        {documents.length ? documents.map((document) => (
          <Link key={document.id} to={`/app/results/${document.id}`} className="grid gap-3 border-b border-black/5 p-4 text-sm hover:bg-black/5 sm:grid-cols-[auto_1fr_auto] sm:items-center dark:border-white/10 dark:hover:bg-white/10">
            <FileText className="h-5 w-5 text-[#007AFF]" />
            <span><span className="block font-semibold">{document.original_filename}</span><span className="text-xs text-[#6E6E73] dark:text-[#A1A1A6]">#{document.id} · {document.document_type}</span></span>
            <span className="flex items-center gap-2"><Badge>{document.processing_status}</Badge><ArrowRight className="h-4 w-4" /></span>
          </Link>
        )) : <EmptyState title="No documents yet." action={<Link to="/app/upload"><Button>Upload to begin</Button></Link>} />}
      </Card>
    </div>
  );
}
