import type { LucideIcon } from "lucide-react";
import { Inbox } from "lucide-react";
import type { ReactNode } from "react";

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
}: {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div
      className="flex flex-col items-center justify-center rounded-xl border border-dashed px-6 py-12 text-center"
      style={{ borderColor: "var(--oma-border)", backgroundColor: "var(--oma-surface)" }}
    >
      <Icon className="mb-3 h-10 w-10" style={{ color: "var(--oma-muted)" }} aria-hidden />
      <p className="text-sm font-medium" style={{ color: "var(--oma-text)" }}>
        {title}
      </p>
      {description && (
        <p className="oma-hint mt-1 max-w-sm">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
