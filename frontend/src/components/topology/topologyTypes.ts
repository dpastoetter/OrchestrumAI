import type { GenericWorkflowAgent } from "../../types";

export type TopologyType = "simple" | "sequential" | "orchestrator";
export type TopologyNodeKind = "catalog" | "custom";

export interface TopologyNode {
  id: string;
  kind: TopologyNodeKind;
  catalog_id?: string;
  name?: string;
  instruction?: string;
}

export interface TopologyEdge {
  from: string;
  to: string;
}

export interface AgentTopology {
  type: TopologyType;
  nodes: TopologyNode[];
  edges: TopologyEdge[];
}

export const COORDINATOR_NODE_ID = "__coordinator__";

export function newNodeId(): string {
  return `n_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`;
}

export function catalogNode(catalogId: string): TopologyNode {
  return { id: newNodeId(), kind: "catalog", catalog_id: catalogId };
}

export function customNode(name: string, instruction: string): TopologyNode {
  return { id: newNodeId(), kind: "custom", name, instruction };
}

export function defaultTopology(
  type: TopologyType,
  catalog: GenericWorkflowAgent[],
): AgentTopology {
  const defaults = catalog.filter((a) => a.default_enabled).map((a) => catalogNode(a.id));
  if (type === "simple") {
    const first = defaults[0] ?? (catalog[0] ? catalogNode(catalog[0].id) : catalogNode("research"));
    return { type: "simple", nodes: [first], edges: [] };
  }
  if (type === "sequential") {
    const nodes =
      defaults.length >= 2
        ? defaults.slice(0, 2)
        : [
            catalog[0] ? catalogNode(catalog[0].id) : catalogNode("research"),
            catalog[1] ? catalogNode(catalog[1].id) : catalogNode("writer"),
          ];
    return { type: "sequential", nodes, edges: chainEdges(nodes) };
  }
  const nodes = defaults.length ? defaults : [catalogNode("research"), catalogNode("writer")];
  return { type: "orchestrator", nodes, edges: [] };
}

export function chainEdges(nodes: TopologyNode[]): TopologyEdge[] {
  const edges: TopologyEdge[] = [];
  for (let i = 0; i < nodes.length - 1; i++) {
    edges.push({ from: nodes[i].id, to: nodes[i + 1].id });
  }
  return edges;
}

export function nodeLabel(
  node: TopologyNode,
  catalog: GenericWorkflowAgent[],
): string {
  if (node.kind === "catalog" && node.catalog_id) {
    return catalog.find((c) => c.id === node.catalog_id)?.name ?? node.catalog_id;
  }
  return node.name?.trim() || "Custom agent";
}

export function validateTopology(topology: AgentTopology): string | null {
  const { type, nodes } = topology;
  if (type === "simple") {
    if (nodes.length !== 1) return "Simple mode requires exactly one agent.";
  } else if (type === "sequential") {
    if (nodes.length < 2) return "Sequential mode requires at least two agents.";
  } else if (type === "orchestrator") {
    if (nodes.length < 1) return "Add at least one delegate agent.";
  }
  for (const n of nodes) {
    if (n.kind === "custom") {
      if (!n.name?.trim()) return "Each custom agent needs a name.";
      if (!n.instruction?.trim()) return `Custom agent "${n.name || "?"}" needs an instruction.`;
    }
  }
  return null;
}

export function topologyForApi(topology: AgentTopology): AgentTopology {
  if (topology.type === "sequential") {
    return { ...topology, edges: chainEdges(topology.nodes) };
  }
  return { ...topology, edges: topology.type === "orchestrator" ? [] : topology.edges };
}
