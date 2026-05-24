import { Loader2 } from "lucide-react";
import { motion } from "framer-motion";

const buttonVariants = {
  primary: "bg-[#007AFF] text-white hover:bg-[#0A84FF]",
  secondary: "border border-black/10 bg-white/75 text-[#1D1D1F] hover:bg-white dark:border-white/10 dark:bg-white/10 dark:text-[#F5F5F7]",
  danger: "bg-[#FF3B30] text-white hover:bg-[#FF453A]",
  success: "bg-[#34C759] text-white hover:bg-[#30D158]",
  ghost: "text-[#1D1D1F] hover:bg-black/5 dark:text-[#F5F5F7] dark:hover:bg-white/10",
};

export function Button({ children, className = "", variant = "primary", loading = false, icon: Icon, type = "button", ...props }) {
  return (
    <motion.button
      type={type}
      whileHover={{ y: props.disabled ? 0 : -1 }}
      whileTap={{ scale: props.disabled ? 1 : 0.98 }}
      className={`focus-ring inline-flex items-center justify-center gap-2 rounded-2xl px-4 py-2.5 text-sm font-semibold shadow-apple-sm transition disabled:cursor-not-allowed disabled:opacity-60 ${buttonVariants[variant]} ${className}`}
      {...props}
    >
      {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : Icon ? <Icon className="h-4 w-4" /> : null}
      {children}
    </motion.button>
  );
}

export function Card({ children, className = "" }) {
  return <div className={`glass-panel rounded-apple p-5 ${className}`}>{children}</div>;
}

export function Badge({ children, tone = "neutral" }) {
  const tones = {
    neutral: "bg-black/5 text-[#6E6E73] dark:bg-white/10 dark:text-[#A1A1A6]",
    info: "bg-[#007AFF]/10 text-[#007AFF] dark:text-[#0A84FF]",
    success: "bg-[#34C759]/10 text-[#1F7A3A] dark:text-[#30D158]",
    warning: "bg-[#FF9500]/10 text-[#A85B00] dark:text-[#FF9F0A]",
    danger: "bg-[#FF3B30]/10 text-[#B42318] dark:text-[#FF453A]",
    violet: "bg-[#AF52DE]/10 text-[#7D35AA] dark:text-[#BF5AF2]",
  };
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${tones[tone] || tones.neutral}`}>{children}</span>;
}

export function Input({ label, icon: Icon, className = "", ...props }) {
  return (
    <label className={`block text-sm font-medium text-[#1D1D1F] dark:text-[#F5F5F7] ${className}`}>
      {label && <span className="mb-1.5 block">{label}</span>}
      <span className="flex items-center gap-2 rounded-2xl border border-black/10 bg-white/80 px-3 py-2.5 shadow-apple-sm focus-within:border-[#007AFF]/40 focus-within:ring-2 focus-within:ring-[#007AFF]/15 dark:border-white/10 dark:bg-white/10">
        {Icon && <Icon className="h-4 w-4 text-[#A1A1A6]" />}
        <input className="min-w-0 flex-1 bg-transparent text-sm outline-none" {...props} />
      </span>
    </label>
  );
}

export function Select({ label, children, className = "", ...props }) {
  return (
    <label className={`block text-sm font-medium text-[#1D1D1F] dark:text-[#F5F5F7] ${className}`}>
      {label && <span className="mb-1.5 block">{label}</span>}
      <select className="focus-ring w-full rounded-2xl border border-black/10 bg-white/80 px-3 py-2.5 text-sm shadow-apple-sm dark:border-white/10 dark:bg-[#1C1C1E]" {...props}>
        {children}
      </select>
    </label>
  );
}

export function Toast({ message, type = "info" }) {
  if (!message) return null;
  return <div className="rounded-2xl border border-black/10 bg-white/80 px-3 py-2 text-sm text-[#6E6E73] shadow-apple-sm dark:border-white/10 dark:bg-white/10 dark:text-[#A1A1A6]">{message}</div>;
}

export function LoadingSpinner({ label = "Loading" }) {
  return (
    <div className="grid min-h-[320px] place-items-center">
      <div className="flex items-center gap-3 rounded-2xl bg-white/80 px-4 py-3 text-sm font-semibold text-[#6E6E73] shadow-apple-sm dark:bg-white/10 dark:text-[#A1A1A6]">
        <Loader2 className="h-4 w-4 animate-spin" />
        {label}
      </div>
    </div>
  );
}

export function RiskBadge({ riskLevel = "Medium Risk" }) {
  const label = riskLevel || "Medium Risk";
  const tone = label.includes("Very Low") || label.includes("Low") ? "success" : label.includes("Medium") ? "warning" : "danger";
  return <Badge tone={tone}>{label}</Badge>;
}

export function EmptyState({ title = "No records found.", action }) {
  return (
    <div className="rounded-apple border border-dashed border-black/10 p-8 text-center dark:border-white/10">
      <p className="text-sm font-semibold text-[#1D1D1F] dark:text-[#F5F5F7]">{title}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
