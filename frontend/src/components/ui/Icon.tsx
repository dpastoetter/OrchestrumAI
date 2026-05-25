import type { LucideIcon } from "lucide-react";

const SIZES = { sm: 14, md: 16, lg: 20, xl: 24 } as const;

export function Icon({
  icon: Lucide,
  size = "md",
  className = "",
}: {
  icon: LucideIcon;
  size?: keyof typeof SIZES;
  className?: string;
}) {
  return <Lucide size={SIZES[size]} className={className} aria-hidden />;
}
