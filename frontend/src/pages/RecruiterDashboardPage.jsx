import { useEffect, useState } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { Badge, Card, LoadingSpinner } from "../components/ui.jsx";
import { getRecruiterStats } from "../services/api.js";

const colors = ["#34C759", "#007AFF", "#FF9500", "#FF3B30", "#AF52DE"];

export default function RecruiterDashboardPage() {
  const [stats, setStats] = useState(null);
  useEffect(() => { getRecruiterStats().then((response) => setStats(response.data)).catch(() => setStats({ recent_verifications: [], risk_distribution: [] })); }, []);
  if (!stats) return <LoadingSpinner label="Loading analytics" />;
  return (
    <div className="space-y-6">
      <Card><Badge tone="info">Recruiter</Badge><h1 className="mt-3 text-2xl font-semibold">Candidate Verification</h1></Card>
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <Metric label="Total Verifications" value={stats.total_documents_verified || 0} />
        <Metric label="Verified" value={stats.verified_count || 0} />
        <Metric label="Review Required" value={stats.manual_review_count || 0} />
        <Metric label="High Risk" value={(stats.likely_fraud_count || 0) + (stats.rejected_count || 0)} />
        <Metric label="Average Score" value={`${Math.round(stats.average_authenticity_score || 0)}%`} />
      </section>
      <Card>
        <h2 className="text-lg font-semibold">Risk Distribution</h2>
        <div className="mt-4 h-72"><ResponsiveContainer><PieChart><Pie data={normalize(stats.risk_distribution)} dataKey="count" nameKey="label" innerRadius={50} outerRadius={88}>{normalize(stats.risk_distribution).map((entry, index) => <Cell key={entry.label} fill={colors[index % colors.length]} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer></div>
      </Card>
    </div>
  );
}

function Metric({ label, value }) {
  return <Card><p className="text-2xl font-semibold">{value}</p><p className="mt-1 text-sm text-[#6E6E73] dark:text-[#A1A1A6]">{label}</p></Card>;
}

function normalize(data = []) {
  return data.length ? data.map((item) => ({ label: item.risk_level?.replaceAll("_", " "), count: item.count })) : [{ label: "No results", count: 1 }];
}
