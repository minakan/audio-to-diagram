from typing import Literal

from pydantic import BaseModel, Field

NodeKind = Literal[
    "variable",
    "array_element",
    "pointer",
    "process_step",
    "condition",
    "data_structure",
    "memory_block",
]

RelationKind = Literal[
    "points_to",
    "contains",
    "updates",
    "transitions_to",
    "compares",
    "calls",
    "depends_on",
    "calculate",
]


class NodeState(BaseModel):
    active: bool = True
    value: str | None = None


class NodeVisual(BaseModel):
    shape: Literal["rectangle", "circle", "diamond"] = "rectangle"
    emphasis: Literal["low", "medium", "high"] = "medium"


class DiagramNode(BaseModel):
    id: str
    label: str
    kind: NodeKind
    description: str
    group: str | None = None
    state: NodeState = Field(default_factory=NodeState)
    visual: NodeVisual = Field(default_factory=NodeVisual)


class EdgeVisual(BaseModel):
    style: Literal["solid", "dashed"] = "solid"
    emphasis: Literal["low", "medium", "high"] = "medium"


class DiagramEdge(BaseModel):
    id: str
    from_node: str = Field(alias="from")
    to_node: str = Field(alias="to")
    relation: RelationKind
    label: str | None = None
    directed: bool = True
    visual: EdgeVisual = Field(default_factory=EdgeVisual)

    model_config = {"populate_by_name": True}


class DiagramAnnotation(BaseModel):
    id: str
    text: str
    target_ids: list[str] = Field(default_factory=list)
    priority: Literal["low", "medium", "high"] = "medium"


class GroupingItem(BaseModel):
    group_id: str
    label: str


class LayoutHint(BaseModel):
    direction: Literal["left_to_right", "top_to_bottom"] = "left_to_right"
    grouping: list[GroupingItem] = Field(default_factory=list)
    preferred_aspect_ratio: str = "16:9"


class SourceInfo(BaseModel):
    session_id: str
    utterance_id: str
    source_text: str


class DiagramPlan(BaseModel):
    schema_version: str = "1.0"
    topic: str
    diagram_type: str
    summary: str
    nodes: list[DiagramNode]
    edges: list[DiagramEdge]
    annotations: list[DiagramAnnotation] = Field(default_factory=list)
    layout: LayoutHint = Field(default_factory=LayoutHint)
    source: SourceInfo
