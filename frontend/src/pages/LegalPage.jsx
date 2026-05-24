import { Link } from "react-router-dom";

import { Badge, Card } from "../components/ui.jsx";

const content = {
  privacy: {
    title: "Privacy Policy",
    points: [
      "Documents are processed for verification workflows.",
      "Access is controlled through authenticated workspace accounts.",
      "Uploaded files should be stored in private storage in production.",
      "Contact support to request data deletion or account assistance.",
    ],
  },
  terms: {
    title: "Terms of Service",
    points: [
      "DocuVerify AI provides AI-assisted, risk-based document verification.",
      "Results support decision-making and do not replace independent review.",
      "Users are responsible for lawful document submission and access.",
      "Manual review is recommended for uncertain cases.",
    ],
  },
  security: {
    title: "Security",
    points: [
      "Authentication uses JWT-based access control.",
      "CORS should be restricted to approved frontend domains.",
      "Sensitive keys must be stored in deployment environment variables.",
      "Do not share private document URLs publicly.",
    ],
  },
  contact: {
    title: "Contact",
    points: [
      `Support email: ${import.meta.env.VITE_CONTACT_EMAIL || "support@docuverify.ai"}`,
      "For workspace access, billing, security, or verification support, contact the team.",
    ],
  },
};

export default function LegalPage({ type = "privacy" }) {
  const page = content[type] || content.privacy;
  return (
    <main className="min-h-screen bg-[#F5F5F7] px-5 py-10 dark:bg-black">
      <div className="mx-auto max-w-3xl">
        <Link to="/" className="text-sm font-semibold text-[#007AFF]">DocuVerify AI</Link>
        <Card className="mt-6">
          <Badge tone="info">Trust</Badge>
          <h1 className="mt-4 text-3xl font-semibold">{page.title}</h1>
          <div className="mt-6 space-y-3">
            {page.points.map((point) => <p key={point} className="rounded-2xl bg-black/5 p-3 text-sm text-[#6E6E73] dark:bg-white/10 dark:text-[#A1A1A6]">{point}</p>)}
          </div>
        </Card>
      </div>
    </main>
  );
}
