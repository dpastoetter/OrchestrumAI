import { Handle, Position, type NodeProps } from "@xyflow/react";
import { LayoutTemplate, Network } from "lucide-react";
import { PaletteCategoryIcons } from "../../lib/icons";
import type { AgentCatalogCategory } from "../../types";
import type { TopologyNode } from "./topologyTypes";

export type AgentFlowNodeData = {
  label: string;
  node: TopologyNode;
  category?: AgentCatalogCategory;
  isCoordinator?: boolean;
  onRemove?: () => void;
  onEdit?: () => void;
};

export function AgentFlowNode({ data, selected }: NodeProps) {
  const d = data as AgentFlowNodeData;
  const category = d.category ?? (d.node.kind === "custom" ? undefined : "writing");
  const CatIcon = category ? PaletteCategoryIcons[category] : LayoutTemplate;

  return (
    <div
      className={[
        "relative min-w-[152px] max-w-[200px] rounded-xl border px-3.5 py-2.5 text-sm shadow-md transition-shadow",
        d.node.kind === "custom" && !d.isCoordinator ? "border-dashed" : "",
        selected ? "ring-2" : "",
      ].join(" ")}
      style={{
        borderColor: d.isCoordinator
          ? "var(--oma-primary)"
          : "var(--oma-border)",
        backgroundColor: "var(--oma-surface)",
        color: "var(--oma-text)",
        boxShadow: selected
          ? "0 0 0 2px color-mix(in srgb, var(--oma-primary) 35%, transparent)"
          : undefined,
      }}
    >
      {!d.isCoordinator && (
        <Handle type="target" position={Position.Left} className="!h-2.5 !w-2.5" />
      )}

      {d.onRemove && (
        <button
          type="button"
          aria-label={`Remove ${d.label}`}
          className="nodrag nopan absolute -right-2 -top-2 flex h-5 w-5 items-center justify-center rounded-full border text-[10px] leading-none transition"
          style={{
            borderColor: "var(--oma-border)",
            backgroundColor: "var(--oma-surface-elevated)",
            color: "var(--oma-muted)",
          }}
          onClick={(e) => {
            e.stopPropagation();
            d.onRemove?.();
          }}
        >
          ×
        </button>
      )}

      <span className="mb-1 flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--oma-muted)" }}>
        {d.isCoordinator ? (
          <>
            <Network size={12} aria-hidden />
            Orchestrator
          </>
        ) : (
          <>
            <CatIcon size={12} aria-hidden />
            {category === "private_doc" ? "Private" : category === "web" ? "Web" : d.node.kind === "custom" ? "Custom" : "Writing"}
          </>
        )}
      </span>

      <p className="font-semibold leading-snug">{d.label}</p>

      {d.node.kind === "custom" && d.node.instruction && (
        <p className="oma-hint mt-1.5 line-clamp-2 text-[11px] leading-relaxed">{d.node.instruction}</p>
      )}

      {d.onEdit && (
        <button
          type="button"
          className="nodrag nopan mt-2 text-[11px] font-medium hover:underline"
          style={{ color: "var(--oma-primary)" }}
          onClick={(e) => {
            e.stopPropagation();
            d.onEdit?.();
          }}
        >
          Edit instruction
        </button>
      )}

      {!d.isCoordinator && <Handle type="source" position={Position.Right} className="!h-2.5 !w-2.5" />}
      {d.isCoordinator && <Handle type="source" position={Position.Bottom} className="!h-2.5 !w-2.5" />}
    </div>
  );
}
