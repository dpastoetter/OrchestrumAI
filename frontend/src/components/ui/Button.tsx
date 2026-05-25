import type { LucideIcon } from "lucide-react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md";

const variantClass: Record<Variant, string> = {
  primary: "oma-btn-primary",
  secondary: "oma-btn-secondary",
  ghost:
    "inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition hover:opacity-80 disabled:opacity-50",
  danger: "oma-btn-danger",
};

const sizeClass: Record<Size, string> = {
  sm: "!px-2.5 !py-1.5 !text-xs",
  md: "",
};

export function Button({
  variant = "primary",
  size = "md",
  icon: Icon,
  children,
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
  icon?: LucideIcon;
  children?: ReactNode;
}) {
  const ghostStyle =
    variant === "ghost"
      ? { color: "var(--oma-muted)", backgroundColor: "transparent" }
      : undefined;

  return (
    <button
      type="button"
      className={`${variantClass[variant]} ${sizeClass[size]} ${className}`}
      style={ghostStyle}
      {...props}
    >
      {Icon && <Icon size={size === "sm" ? 14 : 16} aria-hidden />}
      {children}
    </button>
  );
}
