import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { TopologyNode } from "./topologyTypes";

export type AgentFlowNodeData = {
  label: string;
  node: TopologyNode;
  isCoordinator?: boolean;
  onRemove?: () => void;
  onEdit?: () => void;
};

export function AgentFlowNode({ data }: NodeProps) {
  const d = data as AgentFlowNodeData;
  return (
    <div
      className={[
        "min-w-[140px] rounded-lg border px-3 py-2 text-sm shadow-md",
        d.isCoordinator
          ? "border-sky-600/60 bg-sky-950/80 text-sky-100"
          : "border-slate-600 bg-slate-900 text-slate-100",
      ].join(" ")}
    >
      {!d.isCoordinator && (
        <Handle type="target" position={Position.Left} className="!bg-sky-500" />
      )}
      <p className="font-medium">{d.label}</p>
      {d.node.kind === "custom" && (
        <p className="mt-0.5 text-xs text-slate-500 line-clamp-2">{d.node.instruction}</p>
      )}
      {!d.isCoordinator && (d.onRemove || d.onEdit) && (
        <div className="mt-2 flex gap-1">
          {d.onEdit && (
            <button
              type="button"
              className="text-xs text-sky-400 hover:underline"
              onClick={(e) => {
                e.stopPropagation();
                d.onEdit?.();
              }}
            >
              Edit
            </button>
          )}
          {d.onRemove && (
            <button
              type="button"
              className="text-xs text-red-400 hover:underline"
              onClick={(e) => {
                e.stopPropagation();
                d.onRemove?.();
              }}
            >
              Remove
            </button>
          )}
        </div>
      )}
      {!d.isCoordinator && (
        <Handle type="source" position={Position.Right} className="!bg-sky-500" />
      )}
      {d.isCoordinator && (
        <Handle type="source" position={Position.Bottom} className="!bg-sky-500" />
      )}
    </div>
  );
}
