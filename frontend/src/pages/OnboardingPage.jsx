import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button, Card, Input, Select, Toast } from "../components/ui.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { completeOnboarding } from "../services/api.js";

export default function OnboardingPage() {
  const { refreshUser } = useAuth();
  const navigate = useNavigate();
  const [payload, setPayload] = useState({ use_case: "Individual", workspace_name: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      await completeOnboarding(payload);
      await refreshUser();
      navigate("/app", { replace: true });
    } catch (requestError) {
      setError(requestError.userMessage || "Onboarding failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-[#F5F5F7] px-5 dark:bg-black">
      <Card className="w-full max-w-lg">
        <h1 className="text-2xl font-semibold">Set up your workspace</h1>
        <form onSubmit={submit} className="mt-6 space-y-4">
          <Select label="Use case" value={payload.use_case} onChange={(event) => setPayload((current) => ({ ...current, use_case: event.target.value }))}>
            <option>Individual</option>
            <option>Recruiter</option>
            <option>Institution</option>
          </Select>
          <Input label="Workspace name" value={payload.workspace_name} onChange={(event) => setPayload((current) => ({ ...current, workspace_name: event.target.value }))} />
          <Toast message={error} />
          <Button type="submit" loading={loading} disabled={loading}>Continue</Button>
        </form>
      </Card>
    </main>
  );
}
