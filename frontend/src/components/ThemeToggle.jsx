import { Moon, Sun } from "lucide-react";

import { useTheme } from "../context/ThemeContext.jsx";

export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const Icon = theme === "dark" ? Sun : Moon;
  return (
    <button onClick={toggleTheme} className="focus-ring grid h-10 w-10 place-items-center rounded-2xl border border-black/10 bg-white/75 shadow-apple-sm dark:border-white/10 dark:bg-white/10" aria-label="Toggle theme">
      <Icon className="h-4 w-4" />
    </button>
  );
}
