import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { useInbox } from "../context/InboxContext";
import { NavIcons } from "../lib/icons";
import { OnboardingBanner } from "./OnboardingBanner";
import { ThemeToggle } from "./ThemeToggle";

const navItems: { to: string; label: string; icon: LucideIcon; end?: boolean }[] = [
  { to: "/", label: "Requests", icon: NavIcons.requests, end: true },
  { to: "/workflows", label: "Workflows", icon: NavIcons.workflows },
  { to: "/submit", label: "New request", icon: NavIcons.submit },
  { to: "/settings", label: "Settings", icon: NavIcons.settings },
];

export function AppLayout({ children }: { children: ReactNode }) {
  const Logo = NavIcons.logo;
  const { awaitingCount } = useInbox();

  return (
    <div className="min-h-screen" style={{ backgroundColor: "var(--oma-bg)" }}>
      <header
        className="sticky top-0 z-40 border-b backdrop-blur-md"
        style={{
          borderColor: "var(--oma-border)",
          backgroundColor: "color-mix(in srgb, var(--oma-surface) 92%, transparent)",
        }}
      >
        <div className="mx-auto flex max-w-5xl flex-col gap-4 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div
              className="flex h-9 w-9 items-center justify-center rounded-lg"
              style={{
                backgroundColor: "color-mix(in srgb, var(--oma-primary) 15%, var(--oma-surface))",
                color: "var(--oma-primary)",
              }}
            >
              <Logo className="h-5 w-5" aria-hidden />
            </div>
            <div>
              <h1 className="text-base font-semibold tracking-tight" style={{ color: "var(--oma-text)" }}>
                OrchestrumAI
              </h1>
              <p className="hidden text-xs sm:block" style={{ color: "var(--oma-muted)" }}>
                Personal workflow automation
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 sm:justify-end">
            <nav className="flex flex-wrap gap-1" aria-label="Main">
              {navItems.map(({ to, label, icon: Icon, end }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  className={({ isActive }) =>
                    [
                      "inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition",
                      isActive ? "oma-nav-active shadow-sm" : "oma-nav-link hover:opacity-90",
                    ].join(" ")
                  }
                >
                  <Icon className="h-4 w-4 shrink-0" aria-hidden />
                  <span className="hidden sm:inline">{label}</span>
                  {to === "/" && awaitingCount > 0 && (
                    <span
                      className="ml-0.5 min-w-[1.25rem] rounded-full px-1.5 py-0.5 text-center text-[10px] font-semibold text-white"
                      style={{ backgroundColor: "var(--oma-warning)" }}
                    >
                      {awaitingCount}
                    </span>
                  )}
                </NavLink>
              ))}
            </nav>
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-8">
        <OnboardingBanner />
        {children}
      </main>
    </div>
  );
}
