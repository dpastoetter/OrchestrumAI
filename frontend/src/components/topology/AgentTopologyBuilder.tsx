import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Background,
  Controls,
  ReactFlow,
  type Edge,
  type Node,
  type OnConnect,
  useEdgesState,
  useNodesState,
  type NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import type { GenericWorkflowAgent } from "../../types";
import { AgentFlowNode, type AgentFlowNodeData } from "./AgentFlowNode";
import { CustomAgentDialog } from "./CustomAgentDialog";
import {
  type AgentTopology,
  COORDINATOR_NODE_ID,
  catalogNode,
  chainEdges,
  customNode,
  defaultTopology,
  nodeLabel,
  type TopologyNode,
  type TopologyType,
} from "./topologyTypes";

const MODE_META: Record<
  TopologyType,
  { title: string; blurb: string; icon: string }
> = {
  simple: {
    title: "Simple",
    blurb: "One agent handles planning and execution.",
    icon: "●",
  },
  sequential: {
    title: "Sequential",
    blurb: "Agents run in order: A → B → C.",
    icon: "→",
  },
  orchestrator: {
    title: "Orchestrator",
    blurb: "Coordinator delegates to specialists.",
    icon: "◎",
  },
};

const nodeTypes: NodeTypes = { agentNode: AgentFlowNode };

function layoutX(index: number, total: number, base = 80): number {
  if (total <= 1) return 200;
  const span = 220;
  return base + (index * span) / Math.max(total - 1, 1);
}

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

  const syncFromTopology = useCallback(
    (topology: AgentTopology): { nodes: Node[]; edges: Edge[] } => {
      const flowNodes: Node[] = [];
      const flowEdges: Edge[] = [];

      if (topology.type === "orchestrator") {
        flowNodes.push({
          id: COORDINATOR_NODE_ID,
          type: "agentNode",
          position: { x: 200, y: 40 },
          data: {
            label: "Coordinator",
            node: { id: COORDINATOR_NODE_ID, kind: "catalog" },
            isCoordinator: true,
          } satisfies AgentFlowNodeData,
          draggable: false,
          selectable: false,
        });
        topology.nodes.forEach((n, i) => {
          const cols = 3;
          const row = Math.floor(i / cols);
          const col = i % cols;
          flowNodes.push({
            id: n.id,
            type: "agentNode",
            position: { x: 60 + col * 200, y: 160 + row * 100 },
            data: makeNodeData(n, topology, catalog, disabled, onChange, setPendingCustom),
          });
          flowEdges.push({
            id: `e-${COORDINATOR_NODE_ID}-${n.id}`,
            source: COORDINATOR_NODE_ID,
            target: n.id,
            animated: true,
          });
        });
        return { nodes: flowNodes, edges: flowEdges };
      }

      topology.nodes.forEach((n, i) => {
        flowNodes.push({
          id: n.id,
          type: "agentNode",
          position: {
            x: layoutX(i, topology.nodes.length),
            y: topology.type === "sequential" ? 80 : 120,
          },
          data: makeNodeData(n, topology, catalog, disabled, onChange, setPendingCustom),
        });
      });

      const edges =
        topology.type === "sequential"
          ? chainEdges(topology.nodes).map((e) => ({
              id: `e-${e.from}-${e.to}`,
              source: e.from,
              target: e.to,
              animated: true,
            }))
          : [];

      return { nodes: flowNodes, edges };
    },
    [catalog, disabled, onChange],
  );

  const initial = useMemo(() => syncFromTopology(value), [value, syncFromTopology]);
  const [nodes, setNodes, onNodesChange] = useNodesState(initial.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initial.edges);

  useEffect(() => {
    const next = syncFromTopology(value);
    setNodes(next.nodes);
    setEdges(next.edges);
  }, [value.type, value.nodes, syncFromTopology, setNodes, setEdges]);

  useEffect(() => {
    if (pendingCustom?.editNode) setCustomOpen(true);
  }, [pendingCustom]);

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

  const onConnect: OnConnect = (connection) => {
    if (disabled || value.type !== "sequential") return;
    if (!connection.source || !connection.target) return;
    const newEdge = { from: connection.source, to: connection.target };
    setTopology({
      type: "sequential",
      nodes: value.nodes,
      edges: [...value.edges.filter((e) => e.from !== connection.source), newEdge],
    });
  };

  const onNodeDragStop = useCallback(() => {
    if (disabled || value.type !== "sequential") return;
    const agentNodes = nodes
      .filter((n) => n.id !== COORDINATOR_NODE_ID)
      .sort((a, b) => a.position.x - b.position.x);
    const ordered = agentNodes
      .map((fn) => value.nodes.find((n) => n.id === fn.id))
      .filter((n): n is TopologyNode => n !== undefined);
    if (ordered.length === value.nodes.length) {
      setTopology({ type: "sequential", nodes: ordered, edges: chainEdges(ordered) });
    }
  }, [disabled, nodes, value.nodes, setTopology]);

  const onNodesDelete = useCallback(() => {
    if (disabled) return;
    const deleted = new Set(
      nodes.filter((n) => n.selected && n.id !== COORDINATOR_NODE_ID).map((n) => n.id),
    );
    if (!deleted.size) return;
    const remaining = value.nodes.filter((n) => !deleted.has(n.id));
    if (value.type === "simple") return;
    if (value.type === "sequential") {
      setTopology({ type: "sequential", nodes: remaining, edges: chainEdges(remaining) });
    } else {
      setTopology({ type: "orchestrator", nodes: remaining, edges: [] });
    }
  }, [disabled, nodes, value, setTopology]);

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
          return (
            <button
              key={mode}
              type="button"
              disabled={disabled}
              onClick={() => setMode(mode)}
              className={[
                "rounded-lg border p-3 text-left transition",
                selected
                  ? "border-sky-600/50 bg-sky-950/40 ring-2 ring-sky-500/40"
                  : "border-slate-800 bg-slate-950/50 hover:border-slate-600",
                disabled ? "opacity-50" : "",
              ].join(" ")}
            >
              <span className="text-lg" aria-hidden>
                {meta.icon}
              </span>
              <p className="mt-1 text-sm font-medium text-slate-100">{meta.title}</p>
              <p className="text-xs text-slate-500">{meta.blurb}</p>
            </button>
          );
        })}
      </div>

      <div className="flex flex-wrap gap-2 rounded-lg border border-slate-800 bg-slate-950/50 p-3">
        <span className="w-full text-xs font-medium uppercase tracking-wide text-slate-500">
          Palette
        </span>
        {catalog.map((a) => (
          <button
            key={a.id}
            type="button"
            disabled={disabled}
            onClick={() => addCatalog(a.id)}
            className="rounded border border-slate-700 px-2 py-1 text-xs text-slate-300 hover:border-sky-600 hover:bg-slate-900"
            title={a.description}
          >
            + {a.name}
          </button>
        ))}
        <button
          type="button"
          disabled={disabled}
          onClick={() => {
            setPendingCustom(null);
            setCustomOpen(true);
          }}
          className="rounded border border-dashed border-slate-600 px-2 py-1 text-xs text-slate-400 hover:border-sky-600"
        >
          + Custom agent
        </button>
      </div>

      <div className="h-[280px] rounded-lg border border-slate-800 bg-slate-950/80">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodesDelete={onNodesDelete}
          onNodeDragStop={onNodeDragStop}
          nodeTypes={nodeTypes}
          nodesDraggable={!disabled && value.type !== "simple"}
          nodesConnectable={!disabled && value.type === "sequential"}
          elementsSelectable={!disabled}
          fitView
          proOptions={{ hideAttribution: true }}
        >
          <Background gap={16} color="#334155" />
          <Controls showInteractive={false} />
        </ReactFlow>
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

function makeNodeData(
  n: TopologyNode,
  topology: AgentTopology,
  catalog: GenericWorkflowAgent[],
  disabled: boolean | undefined,
  onChange: (t: AgentTopology) => void,
  setPendingCustom: (v: { editNode?: TopologyNode } | null) => void,
): AgentFlowNodeData {
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
    onRemove: topology.type !== "simple" ? remove : undefined,
    onEdit:
      n.kind === "custom"
        ? () => {
            setPendingCustom({ editNode: n });
          }
        : undefined,
  };
}
