import type { LucideIcon } from "lucide-react";
import { AlertCircle, CheckCircle2, Info } from "lucide-react";
import type { ReactNode } from "react";

type AlertVariant = "info" | "error" | "success";

const styles: Record<AlertVariant, { border: string; bg: string; text: string; icon: LucideIcon }> =
  {
    info: {
      border: "color-mix(in srgb, var(--oma-primary) 35%, var(--oma-border))",
      bg: "color-mix(in srgb, var(--oma-primary) 8%, var(--oma-surface))",
      text: "var(--oma-text)",
      icon: Info,
    },
    error: {
      border: "color-mix(in srgb, var(--oma-danger) 40%, var(--oma-border))",
      bg: "color-mix(in srgb, var(--oma-danger) 8%, var(--oma-surface))",
      text: "var(--oma-danger)",
      icon: AlertCircle,
    },
    success: {
      border: "color-mix(in srgb, var(--oma-success) 40%, var(--oma-border))",
      bg: "color-mix(in srgb, var(--oma-success) 8%, var(--oma-surface))",
      text: "var(--oma-success)",
      icon: CheckCircle2,
    },
  };

export function Alert({
  variant = "info",
  title,
  children,
  action,
}: {
  variant?: AlertVariant;
  title?: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  const s = styles[variant];
  const Icon = s.icon;
  return (
    <div
      className="rounded-xl border p-4"
      style={{ borderColor: s.border, backgroundColor: s.bg }}
      role="alert"
    >
      <div className="flex gap-3">
        <Icon className="mt-0.5 h-5 w-5 shrink-0" style={{ color: s.text }} aria-hidden />
        <div className="min-w-0 flex-1 space-y-2">
          {title && (
            <p className="text-sm font-medium" style={{ color: "var(--oma-text)" }}>
              {title}
            </p>
          )}
          <div className="text-sm" style={{ color: variant === "info" ? "var(--oma-muted)" : s.text }}>
            {children}
          </div>
          {action}
        </div>
      </div>
    </div>
  );
}
