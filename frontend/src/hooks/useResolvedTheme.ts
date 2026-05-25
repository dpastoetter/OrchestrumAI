import { useEffect, useState } from "react";
import { getResolvedTheme, getThemePreference } from "../lib/theme";

export function useResolvedTheme(): "light" | "dark" {
  const [theme, setTheme] = useState<"light" | "dark">(() => getResolvedTheme());

  useEffect(() => {
    const root = document.documentElement;
    const observer = new MutationObserver(() => {
      setTheme(root.classList.contains("dark") ? "dark" : "light");
    });
    observer.observe(root, { attributes: true, attributeFilter: ["class"] });

    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onMq = () => {
      if (getThemePreference() === "system") {
        setTheme(getResolvedTheme());
      }
    };
    mq.addEventListener("change", onMq);

    return () => {
      observer.disconnect();
      mq.removeEventListener("change", onMq);
    };
  }, []);

  return theme;
}
