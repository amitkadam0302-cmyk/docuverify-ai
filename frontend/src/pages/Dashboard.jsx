import { AlertTriangle, CheckCircle2, FileSearch, TrendingUp } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Badge, Button, Card, EmptyState, LoadingSpinner } from "../components/ui.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { getMyDocuments, getRecruiterStats } from "../services/api.js";

const privileged = new Set(["recruiter", "company_admin", "institution_admin", "super_admin"]);

export default function Dashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        if (privileged.has(user?.role)) {
          const response = await getRecruiterStats();
          setData(mapStats(response.data));
        } else {
          const response = await getMyDocuments();
          setData(mapDocuments(response.data));
        }
      } catch {
        setData(mapDocuments([]));
      } finally {
        setLoading(false);
      }
    }
    if (user) load();
  }, [user]);

  if (loading || !data) return <LoadingSpinner label="Loading dashboard" />;

  const cards = [
    { label: "Total Verifications", value: data.total, icon: CheckCircle2 },
    { label: "Average Trust Score", value: `${data.average}%`, icon: TrendingUp },
    { label: "Documents in Review", value: data.review, icon: FileSearch },
    { label: "High-Risk Documents", value: data.highRisk, icon: AlertTriangle },
  ];

  return (
    <div className="space-y-6">
      <Card className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div><Badge tone="info">Overview</Badge><h1 className="mt-3 text-2xl font-semibold">Dashboard</h1></div>
        <Link to="/app/upload"><Button>Verify Document</Button></Link>
      </Card>
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => {
          const Icon = card.icon;
          return <Card key={card.label}><Icon className="h-5 w-5 text-[#007AFF]" /><p className="mt-4 text-2xl font-semibold">{card.value}</p><p className="text-sm text-[#6E6E73] dark:text-[#A1A1A6]">{card.label}</p></Card>;
        })}
      </section>
      <Card>
        <h2 className="text-lg font-semibold">Verification Trends</h2>
        {data.trend.length ? (
          <div className="mt-4 h-72"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data.trend}><XAxis dataKey="day" /><YAxis allowDecimals={false} /><Tooltip /><Area dataKey="count" stroke="#007AFF" fill="#007AFF22" /></AreaChart></ResponsiveContainer></div>
        ) : <EmptyState title="No documents yet." action={<Link to="/app/upload"><Button>Upload to begin</Button></Link>} />}
      </Card>
    </div>
  );
}

function mapStats(stats = {}) {
  const recent = stats.recent_verifications || [];
  return {
    total: stats.total_documents_verified || 0,
    average: Math.round(stats.average_authenticity_score || 0),
    review: stats.manual_review_count || 0,
    highRisk: (stats.likely_fraud_count || 0) + (stats.rejected_count || 0),
    trend: buildTrend(recent.map((item) => item.created_at)),
  };
}

function mapDocuments(documents = []) {
  return { total: documents.length, average: 0, review: documents.filter((item) => item.processing_status !== "completed").length, highRisk: 0, trend: buildTrend(documents.map((item) => item.upload_time)) };
}

function buildTrend(values) {
  const map = new Map();
  values.forEach((value) => {
    const date = value ? new Date(value) : null;
    if (!date || Number.isNaN(date.getTime())) return;
    const key = date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
    map.set(key, (map.get(key) || 0) + 1);
  });
  return Array.from(map, ([day, count]) => ({ day, count })).slice(-7);
}
