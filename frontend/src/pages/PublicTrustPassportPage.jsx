import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { Badge, Card, LoadingSpinner } from "../components/ui.jsx";
import { publicGetTrustPassport } from "../services/api.js";

export default function PublicTrustPassportPage() {
  const { slug } = useParams();
  const [passport, setPassport] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => { publicGetTrustPassport(slug).then((response) => setPassport(response.data)).catch(() => setPassport(null)).finally(() => setLoading(false)); }, [slug]);
  if (loading) return <LoadingSpinner label="Loading Trust Passport" />;
  return (
    <main className="grid min-h-screen place-items-center bg-[#F5F5F7] px-5 dark:bg-black">
      <Card className="w-full max-w-lg">
        <Badge tone="violet">Trust Passport</Badge>
        <h1 className="mt-4 text-2xl font-semibold">{passport?.candidate?.full_name || "Public Profile"}</h1>
        <p className="mt-5 text-5xl font-semibold">{Math.round(passport?.overall_score || 0)}%</p>
        <p className="mt-2 text-sm text-[#6E6E73] dark:text-[#A1A1A6]">Overall Trust Score</p>
      </Card>
    </main>
  );
}
