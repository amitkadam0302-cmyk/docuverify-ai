import { LogOut, Menu, Search } from "lucide-react";

import { useAuth } from "../context/AuthContext.jsx";
import ThemeToggle from "./ThemeToggle.jsx";

export default function Navbar({ title, onMenu }) {
  const { user, logout } = useAuth();
  return (
    <header className="sticky top-0 z-30 border-b border-black/10 bg-white/70 backdrop-blur-2xl dark:border-white/10 dark:bg-black/60">
      <div className="flex min-h-16 items-center gap-3 px-4 sm:px-6">
        <button onClick={onMenu} className="focus-ring rounded-2xl p-2 lg:hidden"><Menu className="h-5 w-5" /></button>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold uppercase text-[#007AFF]">DocuVerify AI</p>
          <h1 className="truncate text-lg font-semibold text-[#1D1D1F] dark:text-[#F5F5F7]">{title}</h1>
        </div>
        <div className="hidden max-w-md flex-1 items-center gap-2 rounded-2xl border border-black/10 bg-white/70 px-3 py-2 dark:border-white/10 dark:bg-white/10 md:flex">
          <Search className="h-4 w-4 text-[#A1A1A6]" />
          <input className="w-full bg-transparent text-sm outline-none" aria-label="Search" />
        </div>
        <ThemeToggle />
        <div className="hidden text-right sm:block">
          <p className="max-w-32 truncate text-xs font-semibold">{user?.full_name}</p>
          <p className="text-[11px] capitalize text-[#6E6E73] dark:text-[#A1A1A6]">{user?.role?.replaceAll("_", " ")}</p>
        </div>
        <button onClick={logout} className="focus-ring grid h-10 w-10 place-items-center rounded-2xl border border-black/10 bg-white/75 text-[#6E6E73] shadow-apple-sm hover:text-[#FF3B30] dark:border-white/10 dark:bg-white/10" title="Sign out">
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
}
