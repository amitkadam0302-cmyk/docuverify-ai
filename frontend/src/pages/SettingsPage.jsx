import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Badge, Button, Card, Input, Toast } from "../components/ui.jsx";
import { getCurrentWorkspace, updateProfileSettings } from "../services/api.js";
import { useAuth } from "../context/AuthContext.jsx";

export default function SettingsPage() {
  const { user, refreshUser } = useAuth();
  const [name, setName] = useState(user?.full_name || "");
  const [workspace, setWorkspace] = useState(null);
  const [message, setMessage] = useState("");
  useEffect(() => { getCurrentWorkspace().then((response) => setWorkspace(response.data)).catch(() => setWorkspace(null)); }, []);
  async function save(event) {
    event.preventDefault();
    await updateProfileSettings({ full_name: name }).then(async () => { await refreshUser(); setMessage("Settings saved."); }).catch((error) => setMessage(error.userMessage || "Save failed."));
  }
  return (
    <div className="space-y-6">
      <Card><Badge tone="info">Settings</Badge><h1 className="mt-3 text-2xl font-semibold">Workspace Settings</h1></Card>
      <Card className="max-w-2xl"><h2 className="text-lg font-semibold">Account Settings</h2><form onSubmit={save} className="mt-4 space-y-4"><Input label="Full name" value={name} onChange={(e) => setName(e.target.value)} /><Toast message={message} /><Button type="submit">Save</Button></form></Card>
      <Card className="max-w-2xl"><h2 className="text-lg font-semibold">Workspace</h2><p className="mt-2 text-sm text-[#6E6E73] dark:text-[#A1A1A6]">{workspace?.name || "Workspace"}</p></Card>
      <Card className="max-w-2xl"><h2 className="text-lg font-semibold">Trust</h2><div className="mt-3 flex flex-wrap gap-3 text-sm text-[#007AFF]"><Link to="/privacy">Privacy Policy</Link><Link to="/terms">Terms of Service</Link><Link to="/security">Security</Link><Link to="/contact">Contact</Link></div></Card>
    </div>
  );
}
