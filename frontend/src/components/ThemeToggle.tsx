import { Monitor, Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import {
  applyTheme,
  getThemePreference,
  setThemePreference,
  type ThemePreference,
} from "../lib/theme";

const OPTIONS: { value: ThemePreference; label: string; Icon: typeof Sun }[] = [
  { value: "light", label: "Light", Icon: Sun },
  { value: "dark", label: "Dark", Icon: Moon },
  { value: "system", label: "System", Icon: Monitor },
];

export function ThemeToggle() {
  const [pref, setPref] = useState<ThemePreference>(() => getThemePreference());

  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      if (getThemePreference() === "system") applyTheme("system");
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  function select(next: ThemePreference) {
    setPref(next);
    setThemePreference(next);
  }

  return (
    <div
      className="inline-flex rounded-lg border p-0.5"
      style={{ borderColor: "var(--oma-border)", backgroundColor: "var(--oma-surface-elevated)" }}
      role="group"
      aria-label="Theme"
    >
      {OPTIONS.map(({ value, label, Icon }) => (
        <button
          key={value}
          type="button"
          title={label}
          onClick={() => select(value)}
          className={[
            "rounded-md p-1.5 transition",
            pref === value ? "shadow-sm" : "opacity-60 hover:opacity-100",
          ].join(" ")}
          style={
            pref === value
              ? { backgroundColor: "var(--oma-surface)", color: "var(--oma-primary)" }
              : { color: "var(--oma-muted)" }
          }
        >
          <Icon className="h-4 w-4" aria-hidden />
        </button>
      ))}
    </div>
  );
}
