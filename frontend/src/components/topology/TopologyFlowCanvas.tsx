import { useCallback, useEffect, useRef } from "react";
import {
  Background,
  BackgroundVariant,
  Controls,
  ReactFlow,
  ReactFlowProvider,
  type Edge,
  type Node,
  type OnConnect,
  type ReactFlowInstance,
  useEdgesState,
  useNodesState,
  type NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import "./topology-flow.css";

import { useResolvedTheme } from "../../hooks/useResolvedTheme";
import { AgentFlowNode, type AgentFlowNodeData } from "./AgentFlowNode";
import {
  type AgentTopology,
  COORDINATOR_NODE_ID,
  chainEdges,
  type TopologyNode,
} from "./topologyTypes";

const nodeTypes: NodeTypes = { agentNode: AgentFlowNode };

const defaultEdgeOptions = {
  type: "smoothstep" as const,
  animated: true,
  style: { stroke: "var(--oma-flow-edge)", strokeWidth: 2 },
};

function delegatePositions(count: number, y: number): { x: number; y: number }[] {
  const slotWidth = 200;
  const totalWidth = Math.max(1, count) * slotWidth;
  const startX = Math.max(40, (640 - totalWidth) / 2);
  return Array.from({ length: count }, (_, i) => ({
    x: startX + i * slotWidth,
    y,
  }));
}

function buildFlowGraph(
  topology: AgentTopology,
  makeData: (n: TopologyNode, topology: AgentTopology) => AgentFlowNodeData,
): { nodes: Node[]; edges: Edge[] } {
  const flowNodes: Node[] = [];
  const flowEdges: Edge[] = [];
  const count = topology.nodes.length;

  if (topology.type === "orchestrator") {
    const centerX = 320;
    flowNodes.push({
      id: COORDINATOR_NODE_ID,
      type: "agentNode",
      position: { x: centerX - 76, y: 24 },
      data: {
        label: "Coordinator",
        node: { id: COORDINATOR_NODE_ID, kind: "catalog" },
        isCoordinator: true,
      } satisfies AgentFlowNodeData,
      draggable: false,
      selectable: false,
    });
    const positions = delegatePositions(count, 200);
    topology.nodes.forEach((n, i) => {
      flowNodes.push({
        id: n.id,
        type: "agentNode",
        position: positions[i] ?? { x: 80 + i * 200, y: 200 },
        data: makeData(n, topology),
      });
      flowEdges.push({
        id: `e-${COORDINATOR_NODE_ID}-${n.id}`,
        source: COORDINATOR_NODE_ID,
        target: n.id,
        ...defaultEdgeOptions,
      });
    });
    return { nodes: flowNodes, edges: flowEdges };
  }

  const positions = delegatePositions(count, topology.type === "sequential" ? 100 : 140);
  topology.nodes.forEach((n, i) => {
    flowNodes.push({
      id: n.id,
      type: "agentNode",
      position: positions[i] ?? { x: 80 + i * 200, y: 120 },
      data: makeData(n, topology),
    });
  });

  if (topology.type === "sequential") {
    chainEdges(topology.nodes).forEach((e) => {
      flowEdges.push({
        id: `e-${e.from}-${e.to}`,
        source: e.from,
        target: e.to,
        ...defaultEdgeOptions,
      });
    });
  }

  return { nodes: flowNodes, edges: flowEdges };
}

interface TopologyFlowCanvasProps {
  topology: AgentTopology;
  disabled?: boolean;
  makeNodeData: (n: TopologyNode, topology: AgentTopology) => AgentFlowNodeData;
  onConnect: OnConnect;
  onSequentialReorder: (ordered: TopologyNode[]) => void;
  onRemoveNodes: (ids: string[]) => void;
}

function TopologyFlowCanvasInner({
  topology,
  disabled,
  makeNodeData,
  onConnect,
  onSequentialReorder,
  onRemoveNodes,
}: TopologyFlowCanvasProps) {
  const rfRef = useRef<ReactFlowInstance | null>(null);
  const colorMode = useResolvedTheme();

  const sync = useCallback(
    () => buildFlowGraph(topology, makeNodeData),
    [topology, makeNodeData],
  );

  const initial = sync();
  const [nodes, setNodes, onNodesChange] = useNodesState(initial.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initial.edges);

  useEffect(() => {
    const next = sync();
    setNodes(next.nodes);
    setEdges(next.edges);
    const t = window.setTimeout(() => {
      rfRef.current?.fitView({ padding: 0.35, duration: 200 });
    }, 50);
    return () => window.clearTimeout(t);
  }, [topology.type, topology.nodes, sync, setNodes, setEdges]);

  const empty = topology.nodes.length === 0;

  const handleNodeDragStop = useCallback(() => {
    if (disabled || topology.type !== "sequential") return;
    const agentNodes = nodes
      .filter((n) => n.id !== COORDINATOR_NODE_ID)
      .sort((a, b) => a.position.x - b.position.x);
    const ordered = agentNodes
      .map((fn) => topology.nodes.find((n) => n.id === fn.id))
      .filter((n): n is TopologyNode => n !== undefined);
    if (ordered.length === topology.nodes.length) {
      onSequentialReorder(ordered);
    }
  }, [disabled, nodes, topology.nodes, topology.type, onSequentialReorder]);

  const handleNodesDelete = useCallback(() => {
    if (disabled) return;
    const deleted = nodes
      .filter((n) => n.selected && n.id !== COORDINATOR_NODE_ID)
      .map((n) => n.id);
    if (deleted.length) onRemoveNodes(deleted);
  }, [disabled, nodes, onRemoveNodes]);

  return (
    <div className="relative h-full min-h-[360px] w-full">
      {empty && (
        <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center p-6">
          <p className="max-w-xs text-center text-sm text-slate-500">
            Add agents from the palette above. They will appear here as connected cards.
          </p>
        </div>
      )}
      <ReactFlow
        className="topology-flow h-full w-full"
        colorMode={colorMode}
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodesDelete={handleNodesDelete}
        onNodeDragStop={handleNodeDragStop}
        onInit={(inst) => {
          rfRef.current = inst;
          inst.fitView({ padding: 0.35, duration: 0 });
        }}
        nodeTypes={nodeTypes}
        defaultEdgeOptions={defaultEdgeOptions}
        nodesDraggable={!disabled && topology.type !== "simple"}
        nodesConnectable={!disabled && topology.type === "sequential"}
        elementsSelectable={!disabled}
        panOnDrag
        zoomOnScroll
        minZoom={0.4}
        maxZoom={1.5}
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="var(--oma-flow-dot)" />
        <Controls
          showInteractive={false}
          position="bottom-right"
          className="!shadow-none"
        />
      </ReactFlow>
    </div>
  );
}

export function TopologyFlowCanvas(props: TopologyFlowCanvasProps) {
  return (
    <ReactFlowProvider>
      <TopologyFlowCanvasInner {...props} />
    </ReactFlowProvider>
  );
}
