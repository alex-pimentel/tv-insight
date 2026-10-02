import { useEffect, useState } from "react";

/**
 * Light/dark switch.
 *
 * The theme is a `class` on `<html>`, applied by an inline script in index.html
 * before the first paint (so there is no flash), and persisted. This component
 * only mirrors that state and lets the user override the system preference.
 */

export type Theme = "light" | "dark";

const STORAGE_KEY = "tv-insight-theme";

export function readTheme(): Theme {
  if (typeof document === "undefined") return "dark";
  return document.documentElement.classList.contains("dark") ? "dark" : "light";
}

export function applyTheme(theme: Theme): void {
  document.documentElement.classList.toggle("dark", theme === "dark");
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // Private mode or blocked storage: the class still applies for this session.
  }
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(() => readTheme());

  // Keep the DOM (the external system) in sync with the chosen theme.
  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  const next: Theme = theme === "dark" ? "light" : "dark";

  return (
    <button
      type="button"
      data-testid="theme-toggle"
      aria-label={`Switch to ${next} theme`}
      aria-pressed={theme === "dark"}
      title={`Switch to ${next} theme`}
      onClick={() => setTheme(next)}
      className="rounded-full bg-overlay px-2.5 py-1 text-[11px] text-muted hover:bg-card-hover"
    >
      <span aria-hidden="true">{theme === "dark" ? "🌙" : "☀️"}</span> {theme}
    </button>
  );
}
