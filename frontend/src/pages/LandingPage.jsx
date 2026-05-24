import { ArrowRight, FileCheck2, Fingerprint, QrCode, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";

import { Badge, Button, Card } from "../components/ui.jsx";

export default function LandingPage() {
  const features = [
    { title: "OCR Extraction", icon: FileCheck2 },
    { title: "Tamper Detection", icon: ShieldCheck },
    { title: "QR Verification", icon: QrCode },
    { title: "Hash Integrity", icon: Fingerprint },
  ];
  return (
    <main className="min-h-screen bg-[#F5F5F7] text-[#1D1D1F] dark:bg-black dark:text-[#F5F5F7]">
      <nav className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5">
        <Link to="/" className="flex items-center gap-3 font-semibold"><ShieldCheck className="h-6 w-6 text-[#007AFF]" /> DocuVerify AI</Link>
        <div className="flex items-center gap-2">
          <Link to="/login" className="rounded-2xl px-3 py-2 text-sm font-semibold text-[#6E6E73] hover:bg-black/5 dark:text-[#A1A1A6] dark:hover:bg-white/10">Sign in</Link>
          <Link to="/register"><Button>Start Verification</Button></Link>
        </div>
      </nav>
      <section className="mx-auto grid max-w-7xl gap-10 px-5 py-16 lg:grid-cols-[1fr_0.82fr] lg:items-center">
        <div>
          <Badge tone="info">Document trust, simplified.</Badge>
          <h1 className="mt-5 max-w-3xl text-5xl font-semibold tracking-tight sm:text-6xl">Document trust, simplified.</h1>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-[#6E6E73] dark:text-[#A1A1A6]">Verify certificates, resumes, and sensitive documents with AI-powered authenticity checks.</p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link to="/register"><Button className="w-full sm:w-auto" icon={ArrowRight}>Start Verification</Button></Link>
            <Link to="/login"><Button variant="secondary" className="w-full sm:w-auto">Explore Platform</Button></Link>
          </div>
        </div>
        <Card className="p-6">
          <div className="rounded-apple bg-white p-5 shadow-apple-sm dark:bg-[#1C1C1E]">
            <p className="text-sm font-semibold text-[#6E6E73] dark:text-[#A1A1A6]">Authenticity Score</p>
            <p className="mt-3 text-5xl font-semibold">82%</p>
            <div className="mt-6 grid gap-3">
              {["Risk Medium", "QR Check Failed", "Hash Check Passed", "Tamper Check Review"].map((item) => <div key={item} className="rounded-2xl bg-black/5 px-4 py-3 text-sm font-semibold dark:bg-white/10">{item}</div>)}
            </div>
          </div>
        </Card>
      </section>
      <section className="mx-auto grid max-w-7xl gap-4 px-5 pb-16 sm:grid-cols-2 lg:grid-cols-4">
        {features.map((feature) => {
          const Icon = feature.icon;
          return <Card key={feature.title}><Icon className="h-5 w-5 text-[#007AFF]" /><p className="mt-4 font-semibold">{feature.title}</p></Card>;
        })}
      </section>
    </main>
  );
}
