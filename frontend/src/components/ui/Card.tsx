import type { ReactNode } from "react";

export function Card({
  children,
  className = "",
  padding = true,
}: {
  children: ReactNode;
  className?: string;
  padding?: boolean;
}) {
  return (
    <div
      className={[
        "rounded-xl border",
        padding ? "p-5" : "",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      style={{
        borderColor: "var(--oma-border)",
        backgroundColor: "var(--oma-surface)",
      }}
    >
      {children}
    </div>
  );
}
