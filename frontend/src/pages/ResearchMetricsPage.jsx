import { useEffect, useState } from "react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Badge, Card, LoadingSpinner } from "../components/ui.jsx";
import { getResearchMetrics } from "../services/api.js";

export default function ResearchMetricsPage() {
  const [metrics, setMetrics] = useState(null);
  useEffect(() => { getResearchMetrics().then((response) => setMetrics(response.data)).catch(() => setMetrics({ ocr_accuracy: [] })); }, []);
  if (!metrics) return <LoadingSpinner label="Loading metrics" />;
  return (
    <div className="space-y-6">
      <Card><Badge tone="info">Research</Badge><h1 className="mt-3 text-2xl font-semibold">Research Metrics</h1></Card>
      <Card><h2 className="text-lg font-semibold">OCR Accuracy</h2><div className="mt-4 h-72"><ResponsiveContainer><BarChart data={metrics.ocr_accuracy || []}><XAxis dataKey="document_type" /><YAxis /><Tooltip /><Bar dataKey="accuracy" fill="#007AFF" /></BarChart></ResponsiveContainer></div></Card>
    </div>
  );
}
