import type { LucideIcon } from "lucide-react";
import {
  AlertCircle,
  Calendar,
  CheckCircle2,
  CircleDashed,
  XCircle,
} from "lucide-react";

export type BadgeVariant =
  | "active"
  | "awaiting"
  | "done"
  | "failed"
  | "scheduled"
  | "neutral";

const config: Record<
  BadgeVariant,
  { icon: LucideIcon; className: string }
> = {
  active: {
    icon: CircleDashed,
    className:
      "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300",
  },
  awaiting: {
    icon: AlertCircle,
    className:
      "bg-amber-50 text-amber-800 dark:bg-amber-950/50 dark:text-amber-200",
  },
  done: {
    icon: CheckCircle2,
    className:
      "bg-emerald-50 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-200",
  },
  failed: {
    icon: XCircle,
    className: "bg-red-50 text-red-800 dark:bg-red-950/50 dark:text-red-200",
  },
  scheduled: {
    icon: Calendar,
    className:
      "bg-violet-50 text-violet-800 dark:bg-violet-950/50 dark:text-violet-200",
  },
  neutral: {
    icon: CircleDashed,
    className:
      "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400",
  },
};

export function statusToBadgeVariant(
  status: string,
): BadgeVariant {
  if (status === "awaiting_approval") return "awaiting";
  if (status === "done") return "done";
  if (status === "failed") return "failed";
  if (status === "active") return "active";
  return "neutral";
}

export function Badge({
  variant,
  children,
  icon,
}: {
  variant: BadgeVariant;
  children: React.ReactNode;
  icon?: LucideIcon;
}) {
  const { icon: DefaultIcon, className } = config[variant];
  const Icon = icon ?? DefaultIcon;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium ${className}`}
    >
      <Icon size={12} aria-hidden />
      {children}
    </span>
  );
}
