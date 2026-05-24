import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";

import Navbar from "../components/Navbar.jsx";
import Sidebar from "../components/Sidebar.jsx";

const titles = {
  "/app": "Dashboard",
  "/app/upload": "Upload Document",
  "/app/history": "Results",
  "/app/batch": "Batch Verification",
  "/app/manual-reviews": "Review Queue",
  "/app/candidates": "Candidates",
  "/app/trust-passport": "Trust Passport",
  "/app/institution": "Institution Portal",
  "/app/recruiter": "Recruiter Analytics",
  "/app/research": "Research Metrics",
  "/app/settings": "Workspace Settings",
  "/dashboard": "Dashboard",
  "/upload": "Upload Document",
  "/history": "Results",
  "/settings": "Workspace Settings",
};

export default function DashboardLayout() {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const title = titles[location.pathname] || "Verification Result";
  return (
    <div className="min-h-screen overflow-x-hidden bg-[#F5F5F7] text-[#1D1D1F] dark:bg-black dark:text-[#F5F5F7]">
      <div className="flex min-h-screen">
        <Sidebar open={open} onClose={() => setOpen(false)} />
        <div className="min-w-0 flex-1">
          <Navbar title={title} onMenu={() => setOpen(true)} />
          <main className="px-4 py-6 sm:px-6 lg:px-8">
            <div className="mx-auto max-w-7xl">
              <Outlet />
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
