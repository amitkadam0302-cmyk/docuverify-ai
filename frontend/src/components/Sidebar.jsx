import { BarChart3, ClipboardCheck, FileClock, Files, Gauge, LockKeyhole, Microscope, Settings, ShieldCheck, UploadCloud, UserRound } from "lucide-react";
import { NavLink } from "react-router-dom";

import { useAuth } from "../context/AuthContext.jsx";

const links = [
  { to: "/app", label: "Dashboard", icon: Gauge, end: true, roles: ["student", "recruiter", "institution_admin", "company_admin", "super_admin"] },
  { to: "/app/upload", label: "Upload Document", icon: UploadCloud, roles: ["student", "recruiter", "institution_admin", "company_admin", "super_admin"] },
  { to: "/app/history", label: "My Results", icon: FileClock, roles: ["student", "recruiter", "institution_admin", "company_admin", "super_admin"] },
  { to: "/app/candidates", label: "Candidates", icon: UserRound, roles: ["recruiter", "company_admin", "super_admin"] },
  { to: "/app/trust-passport", label: "Trust Passport", icon: ShieldCheck, roles: ["student", "recruiter", "company_admin", "super_admin"] },
  { to: "/app/batch", label: "Batch Verification", icon: Files, roles: ["recruiter", "company_admin", "super_admin"] },
  { to: "/app/manual-reviews", label: "Manual Review", icon: ClipboardCheck, roles: ["recruiter", "institution_admin", "company_admin", "super_admin"] },
  { to: "/app/institution", label: "Institution Portal", icon: LockKeyhole, roles: ["institution_admin", "super_admin"] },
  { to: "/app/recruiter", label: "Recruiter Analytics", icon: BarChart3, roles: ["recruiter", "company_admin", "super_admin"] },
  { to: "/app/research", label: "Research Metrics", icon: Microscope, roles: ["recruiter", "institution_admin", "company_admin", "super_admin"] },
  { to: "/app/settings", label: "Settings", icon: Settings, roles: ["student", "recruiter", "institution_admin", "company_admin", "super_admin"] },
];

export default function Sidebar({ open, onClose }) {
  const { user } = useAuth();
  const visible = links.filter((link) => link.roles.includes(user?.role));
  return (
    <>
      <aside className="sticky top-0 hidden h-screen w-72 shrink-0 border-r border-black/10 bg-white/70 p-3 backdrop-blur-2xl dark:border-white/10 dark:bg-black/60 lg:block">
        <SidebarContent links={visible} user={user} />
      </aside>
      {open && (
        <div className="fixed inset-0 z-50 bg-black/30 backdrop-blur-sm lg:hidden" onClick={onClose}>
          <aside className="h-full w-80 max-w-[86vw] bg-white p-3 dark:bg-[#1C1C1E]" onClick={(event) => event.stopPropagation()}>
            <SidebarContent links={visible} user={user} onClose={onClose} />
          </aside>
        </div>
      )}
    </>
  );
}

function SidebarContent({ links, user, onClose }) {
  return (
    <div className="flex h-full flex-col">
      <NavLink to="/app" onClick={onClose} className="mb-4 flex items-center gap-3 rounded-apple px-2 py-3">
        <span className="grid h-10 w-10 place-items-center rounded-2xl bg-[#007AFF] text-white"><ShieldCheck className="h-5 w-5" /></span>
        <span>
          <span className="block text-sm font-semibold text-[#1D1D1F] dark:text-[#F5F5F7]">DocuVerify AI</span>
          <span className="block text-xs text-[#6E6E73] dark:text-[#A1A1A6]">Document trust</span>
        </span>
      </NavLink>
      <nav className="flex-1 space-y-1">
        {links.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={onClose}
              className={({ isActive }) => `flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm font-semibold transition ${isActive ? "bg-[#007AFF] text-white" : "text-[#6E6E73] hover:bg-black/5 dark:text-[#A1A1A6] dark:hover:bg-white/10"}`}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          );
        })}
      </nav>
      <div className="rounded-apple bg-black/5 p-3 dark:bg-white/10">
        <p className="truncate text-sm font-semibold text-[#1D1D1F] dark:text-[#F5F5F7]">{user?.full_name || "User"}</p>
        <p className="text-xs capitalize text-[#6E6E73] dark:text-[#A1A1A6]">{user?.role?.replaceAll("_", " ") || "member"}</p>
      </div>
    </div>
  );
}
