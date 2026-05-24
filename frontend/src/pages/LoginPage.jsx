import { Eye, EyeOff, LockKeyhole, Mail, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { Button, Card, Input, Toast } from "../components/ui.jsx";
import { useAuth } from "../context/AuthContext.jsx";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      await login(email, password);
      navigate(location.state?.from?.pathname || "/app", { replace: true });
    } catch (requestError) {
      setError(requestError.userMessage || "Login failed. Check your credentials.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthPage title="Welcome back" subtitle="Open your verification workspace.">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input label="Email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" required icon={Mail} />
        <label className="block text-sm font-medium">
          <span className="mb-1.5 block">Password</span>
          <span className="flex items-center gap-2 rounded-2xl border border-black/10 bg-white/80 px-3 py-2.5 shadow-apple-sm dark:border-white/10 dark:bg-white/10">
            <LockKeyhole className="h-4 w-4 text-[#A1A1A6]" />
            <input type={showPassword ? "text" : "password"} value={password} onChange={(event) => setPassword(event.target.value)} className="min-w-0 flex-1 bg-transparent text-sm outline-none" autoComplete="current-password" required />
            <button type="button" onClick={() => setShowPassword((current) => !current)}>{showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button>
          </span>
        </label>
        <Toast message={error} type="error" />
        <Button type="submit" loading={loading} disabled={loading} className="w-full">Sign in</Button>
      </form>
      <p className="mt-5 text-center text-sm text-[#6E6E73] dark:text-[#A1A1A6]">New here? <Link to="/register" className="font-semibold text-[#007AFF]">Create an account</Link></p>
    </AuthPage>
  );
}

export function AuthPage({ title, subtitle, children }) {
  return (
    <main className="grid min-h-screen place-items-center bg-[#F5F5F7] px-5 py-10 dark:bg-black">
      <Card className="w-full max-w-md p-7">
        <Link to="/" className="mb-6 flex items-center gap-3">
          <span className="grid h-11 w-11 place-items-center rounded-2xl bg-[#007AFF] text-white"><ShieldCheck className="h-5 w-5" /></span>
          <span className="font-semibold">DocuVerify AI</span>
        </Link>
        <h1 className="text-2xl font-semibold">{title}</h1>
        <p className="mt-2 text-sm text-[#6E6E73] dark:text-[#A1A1A6]">{subtitle}</p>
        <div className="mt-6">{children}</div>
      </Card>
    </main>
  );
}
