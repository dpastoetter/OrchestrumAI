import { Plus } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { PaletteCategoryIcons, TopologyModeIcons } from "../../lib/icons";
import type { GenericWorkflowAgent } from "../../types";
import { type AgentFlowNodeData } from "./AgentFlowNode";
import { CustomAgentDialog } from "./CustomAgentDialog";
import { TopologyFlowCanvas } from "./TopologyFlowCanvas";
import {
  type AgentTopology,
  catalogNode,
  chainEdges,
  customNode,
  defaultTopology,
  nodeLabel,
  type TopologyNode,
  type TopologyType,
} from "./topologyTypes";

const PALETTE_GROUPS: { category: "private_doc" | "writing" | "web"; label: string }[] = [
  { category: "private_doc", label: "Private documents" },
  { category: "writing", label: "Writing" },
  { category: "web", label: "Web research" },
];

const MODE_META: Record<TopologyType, { title: string; blurb: string }> = {
  simple: {
    title: "Simple",
    blurb: "One agent handles planning and execution.",
  },
  sequential: {
    title: "Sequential",
    blurb: "Agents run in order: A → B → C.",
  },
  orchestrator: {
    title: "Orchestrator",
    blurb: "Coordinator delegates to specialists.",
  },
};

interface AgentTopologyBuilderProps {
  catalog: GenericWorkflowAgent[];
  value: AgentTopology;
  onChange: (topology: AgentTopology) => void;
  disabled?: boolean;
}

export function AgentTopologyBuilder({
  catalog,
  value,
  onChange,
  disabled,
}: AgentTopologyBuilderProps) {
  const [customOpen, setCustomOpen] = useState(false);
  const [pendingCustom, setPendingCustom] = useState<{
    replaceId?: string;
    editNode?: TopologyNode;
  } | null>(null);

  const setTopology = useCallback(
    (next: AgentTopology) => {
      onChange(next);
    },
    [onChange],
  );

  const setMode = (type: TopologyType) => {
    if (disabled) return;
    setTopology(defaultTopology(type, catalog));
  };

  const addCatalog = (catalogId: string) => {
    if (disabled) return;
    const n = catalogNode(catalogId);
    if (value.type === "simple") {
      setTopology({ type: "simple", nodes: [n], edges: [] });
      return;
    }
    if (value.type === "sequential") {
      const nodes = [...value.nodes, n];
      setTopology({ type: "sequential", nodes, edges: chainEdges(nodes) });
      return;
    }
    setTopology({ type: "orchestrator", nodes: [...value.nodes, n], edges: [] });
  };

  const onConnect = (connection: { source?: string | null; target?: string | null }) => {
    if (disabled || value.type !== "sequential") return;
    if (!connection.source || !connection.target) return;
    const newEdge = { from: connection.source, to: connection.target };
    setTopology({
      type: "sequential",
      nodes: value.nodes,
      edges: [...value.edges.filter((e) => e.from !== connection.source), newEdge],
    });
  };

  const onSequentialReorder = (ordered: TopologyNode[]) => {
    setTopology({ type: "sequential", nodes: ordered, edges: chainEdges(ordered) });
  };

  const onRemoveNodes = (ids: string[]) => {
    const deleted = new Set(ids);
    const remaining = value.nodes.filter((n) => !deleted.has(n.id));
    if (value.type === "simple") return;
    if (value.type === "sequential") {
      setTopology({ type: "sequential", nodes: remaining, edges: chainEdges(remaining) });
    } else {
      setTopology({ type: "orchestrator", nodes: remaining, edges: [] });
    }
  };

  useEffect(() => {
    if (pendingCustom?.editNode) setCustomOpen(true);
  }, [pendingCustom]);

  const makeNodeData = useCallback(
    (n: TopologyNode, topology: AgentTopology): AgentFlowNodeData => {
      const catalogEntry =
        n.kind === "catalog" ? catalog.find((a) => a.id === n.catalog_id) : undefined;
      const remove = () => {
        if (disabled) return;
        const remaining = topology.nodes.filter((x) => x.id !== n.id);
        if (topology.type === "simple") return;
        if (topology.type === "sequential") {
          onChange({ type: "sequential", nodes: remaining, edges: chainEdges(remaining) });
        } else {
          onChange({ type: "orchestrator", nodes: remaining, edges: [] });
        }
      };
      return {
        label: nodeLabel(n, catalog),
        node: n,
        category: catalogEntry?.category,
        onRemove: topology.type !== "simple" ? remove : undefined,
        onEdit:
          n.kind === "custom"
            ? () => {
                setPendingCustom({ editNode: n });
              }
            : undefined,
      };
    },
    [catalog, disabled, onChange],
  );

  return (
    <section className="oma-section space-y-4">
      <div>
        <h3 className="oma-label">Agent interaction</h3>
        <p className="oma-hint mt-0.5">
          Drag specialists from the palette onto the canvas. How agents work together applies to
          this request only.
        </p>
      </div>

      <div className="grid gap-2 sm:grid-cols-3">
        {(Object.keys(MODE_META) as TopologyType[]).map((mode) => {
          const meta = MODE_META[mode];
          const selected = value.type === mode;
          const ModeIcon = TopologyModeIcons[mode];
          return (
            <button
              key={mode}
              type="button"
              disabled={disabled}
              onClick={() => setMode(mode)}
              className={["rounded-lg border p-3 text-left transition", disabled ? "opacity-50" : ""].join(
                " ",
              )}
              style={{
                borderColor: selected ? "var(--oma-primary)" : "var(--oma-border)",
                backgroundColor: selected
                  ? "color-mix(in srgb, var(--oma-primary) 8%, var(--oma-surface))"
                  : "var(--oma-surface-elevated)",
                boxShadow: selected ? "0 0 0 2px color-mix(in srgb, var(--oma-primary) 25%, transparent)" : undefined,
              }}
            >
              <ModeIcon size={22} style={{ color: "var(--oma-primary)" }} aria-hidden />
              <p className="mt-2 text-sm font-medium" style={{ color: "var(--oma-text)" }}>
                {meta.title}
              </p>
              <p className="oma-hint">{meta.blurb}</p>
            </button>
          );
        })}
      </div>

      <div
        className="space-y-3 rounded-lg border p-3"
        style={{ borderColor: "var(--oma-border)", backgroundColor: "var(--oma-surface-elevated)" }}
      >
        <span className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--oma-muted)" }}>
          Palette
        </span>
        {PALETTE_GROUPS.map((group) => {
          const items = catalog.filter(
            (a) => (a.category ?? "writing") === group.category,
          );
          if (items.length === 0) return null;
          const CatIcon = PaletteCategoryIcons[group.category];
          return (
            <div key={group.category} className="space-y-1.5">
              <span className="flex items-center gap-1.5 text-xs" style={{ color: "var(--oma-muted)" }}>
                <CatIcon size={14} aria-hidden />
                {group.label}
              </span>
              <div className="flex flex-wrap gap-2">
                {items.map((a) => (
                  <button
                    key={a.id}
                    type="button"
                    disabled={disabled}
                    onClick={() => addCatalog(a.id)}
                    className="inline-flex items-center gap-1 rounded-lg border px-2 py-1 text-xs transition hover:opacity-90"
                    style={{ borderColor: "var(--oma-border)", color: "var(--oma-text)" }}
                    title={a.description}
                  >
                    <Plus size={12} aria-hidden />
                    {a.name}
                  </button>
                ))}
              </div>
            </div>
          );
        })}
        <div className="space-y-1.5">
          <span className="text-xs" style={{ color: "var(--oma-muted)" }}>
            Custom
          </span>
          <button
            type="button"
            disabled={disabled}
            onClick={() => {
              setPendingCustom(null);
              setCustomOpen(true);
            }}
            className="inline-flex items-center gap-1 rounded-lg border border-dashed px-2 py-1 text-xs transition"
            style={{ borderColor: "var(--oma-muted)", color: "var(--oma-muted)" }}
          >
            <Plus size={12} aria-hidden />
            Custom agent
          </button>
        </div>
      </div>

      <div
        className="h-[380px] overflow-hidden rounded-xl border"
        style={{ borderColor: "var(--oma-border)", backgroundColor: "var(--oma-surface-elevated)" }}
      >
        <TopologyFlowCanvas
          topology={value}
          disabled={disabled}
          makeNodeData={makeNodeData}
          onConnect={onConnect}
          onSequentialReorder={onSequentialReorder}
          onRemoveNodes={onRemoveNodes}
        />
      </div>

      <CustomAgentDialog
        open={customOpen}
        title={pendingCustom?.editNode ? "Edit custom agent" : "Add custom agent"}
        initialName={pendingCustom?.editNode?.name ?? ""}
        initialInstruction={pendingCustom?.editNode?.instruction ?? ""}
        onCancel={() => {
          setCustomOpen(false);
          setPendingCustom(null);
        }}
        onSave={(name, instruction) => {
          if (pendingCustom?.editNode) {
            const updated = value.nodes.map((n) =>
              n.id === pendingCustom.editNode!.id
                ? { ...n, name, instruction }
                : n,
            );
            setTopology({ ...value, nodes: updated });
          } else {
            const n = customNode(name, instruction);
            if (value.type === "simple") {
              setTopology({ type: "simple", nodes: [n], edges: [] });
            } else if (value.type === "sequential") {
              const nodes = [...value.nodes, n];
              setTopology({ type: "sequential", nodes, edges: chainEdges(nodes) });
            } else {
              setTopology({ type: "orchestrator", nodes: [...value.nodes, n], edges: [] });
            }
          }
          setCustomOpen(false);
          setPendingCustom(null);
        }}
      />
    </section>
  );
}
