import { Mail, UserRound } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Button, Input, Select, Toast } from "../components/ui.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { AuthPage } from "./LoginPage.jsx";

export default function RegisterPage() {
  const { register, login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ full_name: "", email: "", password: "", role: "student" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      await register(form);
      await login(form.email, form.password);
      navigate("/onboarding", { replace: true });
    } catch (requestError) {
      setError(requestError.userMessage || "Registration failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthPage title="Create account" subtitle="Start your verification workspace.">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input label="Full name" value={form.full_name} onChange={(event) => update("full_name", event.target.value)} required icon={UserRound} />
        <Input label="Email" type="email" value={form.email} onChange={(event) => update("email", event.target.value)} required icon={Mail} />
        <Input label="Password" type="password" value={form.password} onChange={(event) => update("password", event.target.value)} minLength={8} required />
        <Select label="Role" value={form.role} onChange={(event) => update("role", event.target.value)}>
          <option value="student">Student / Candidate</option>
          <option value="recruiter">Recruiter</option>
        </Select>
        <Toast message={error} type="error" />
        <Button type="submit" loading={loading} disabled={loading} className="w-full">Create account</Button>
      </form>
      <p className="mt-5 text-center text-sm text-[#6E6E73] dark:text-[#A1A1A6]">Already registered? <Link to="/login" className="font-semibold text-[#007AFF]">Sign in</Link></p>
    </AuthPage>
  );
}
