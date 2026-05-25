export type ThemePreference = "light" | "dark" | "system";

const STORAGE_KEY = "orchestrumai_theme";

function systemPrefersDark(): boolean {
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function resolveTheme(pref: ThemePreference): "light" | "dark" {
  if (pref === "system") return systemPrefersDark() ? "dark" : "light";
  return pref;
}

export function getThemePreference(): ThemePreference {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "light" || stored === "dark" || stored === "system") return stored;
  return "system";
}

export function getResolvedTheme(): "light" | "dark" {
  return resolveTheme(getThemePreference());
}

export function applyTheme(pref: ThemePreference): "light" | "dark" {
  const resolved = resolveTheme(pref);
  const root = document.documentElement;
  root.classList.remove("light", "dark");
  root.classList.add(resolved);
  root.style.colorScheme = resolved;
  return resolved;
}

export function setThemePreference(pref: ThemePreference): "light" | "dark" {
  localStorage.setItem(STORAGE_KEY, pref);
  return applyTheme(pref);
}

/** Call once before React mount to avoid flash */
export function initTheme(): void {
  applyTheme(getThemePreference());
}
