"""Per-request agent interaction topology (simple, sequential, orchestrator)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from .generic_agents.catalog import _CATALOG_BY_ID, _VALID_IDS

TopologyType = Literal["simple", "sequential", "orchestrator"]
NodeKind = Literal["catalog", "custom"]

MAX_CUSTOM_NAME = 80
MAX_CUSTOM_INSTRUCTION = 4000
MAX_NODES = 12


class TopologyEdge(BaseModel):
    from_id: str = Field(alias="from")
    to_id: str = Field(alias="to")

    model_config = {"populate_by_name": True}


class TopologyNode(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    kind: NodeKind
    catalog_id: str | None = None
    name: str = Field(default="", max_length=MAX_CUSTOM_NAME)
    instruction: str = Field(default="", max_length=MAX_CUSTOM_INSTRUCTION)

    @model_validator(mode="after")
    def validate_node(self) -> TopologyNode:
        if self.kind == "catalog":
            if not self.catalog_id or self.catalog_id not in _VALID_IDS:
                raise ValueError(f"Invalid catalog_id: {self.catalog_id}")
        elif self.kind == "custom":
            if not self.name.strip():
                raise ValueError("Custom agents require a name")
            if not self.instruction.strip():
                raise ValueError("Custom agents require an instruction")
        return self


class AgentTopology(BaseModel):
    type: TopologyType
    nodes: list[TopologyNode] = Field(default_factory=list)
    edges: list[TopologyEdge] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_topology(self) -> AgentTopology:
        if len(self.nodes) > MAX_NODES:
            raise ValueError(f"At most {MAX_NODES} nodes allowed")
        ids = [n.id for n in self.nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate node ids")

        if self.type == "simple":
            if len(self.nodes) != 1:
                raise ValueError("Simple topology requires exactly one agent node")
        elif self.type == "sequential":
            if len(self.nodes) < 2:
                raise ValueError("Sequential topology requires at least two agent nodes")
            self._validate_chain(ids)
        elif self.type == "orchestrator":
            if len(self.nodes) < 1:
                raise ValueError("Orchestrator topology requires at least one delegate agent")
        return self

    def _validate_chain(self, node_ids: list[str]) -> None:
        if not self.edges:
            return
        by_from: dict[str, str] = {}
        for e in self.edges:
            if e.from_id in by_from:
                raise ValueError("Sequential edges must form a single chain")
            by_from[e.from_id] = e.to_id
            if e.from_id not in node_ids or e.to_id not in node_ids:
                raise ValueError("Edge references unknown node id")
        incoming = {e.to_id for e in self.edges}
        heads = [nid for nid in node_ids if nid not in incoming]
        if len(heads) != 1:
            raise ValueError("Sequential edges must form exactly one chain")

    def ordered_nodes(self) -> list[TopologyNode]:
        """Return nodes in execution order (list order if no edges)."""
        if self.type != "sequential" or not self.edges:
            return list(self.nodes)
        by_from = {e.from_id: e.to_id for e in self.edges}
        incoming = {e.to_id for e in self.edges}
        id_to_node = {n.id: n for n in self.nodes}
        heads = [n.id for n in self.nodes if n.id not in incoming]
        if not heads:
            return list(self.nodes)
        order: list[TopologyNode] = []
        cur: str | None = heads[0]
        seen: set[str] = set()
        while cur and cur not in seen:
            seen.add(cur)
            order.append(id_to_node[cur])
            cur = by_from.get(cur)
        if len(order) != len(self.nodes):
            return list(self.nodes)
        return order

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> AgentTopology | None:
        if not data:
            return None
        return cls.model_validate(data)

    def summary_labels(self) -> list[str]:
        labels: list[str] = []
        for n in self.nodes:
            if n.kind == "catalog" and n.catalog_id:
                defn = _CATALOG_BY_ID.get(n.catalog_id)
                labels.append(defn.name if defn else n.catalog_id)
            else:
                labels.append(n.name.strip() or "Custom")
        return labels
