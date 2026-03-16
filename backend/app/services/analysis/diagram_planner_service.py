import re

from app.schemas.analysis import AnalysisResult
from app.schemas.diagram_plan import (
    DiagramAnnotation,
    DiagramEdge,
    DiagramNode,
    DiagramPlan,
    GroupingItem,
    LayoutHint,
    NodeState,
    NodeVisual,
    SourceInfo,
)


class DiagramPlannerService:
    async def plan(
        self,
        normalized_text: str,
        analysis: AnalysisResult,
    ) -> DiagramPlan:
        lowered = normalized_text.lower()
        if "二分探索" in normalized_text or "binary search" in lowered:
            return self._build_binary_search_plan(normalized_text, analysis)
        return self._build_generic_process_plan(normalized_text, analysis)

    def _build_binary_search_plan(self, text: str, analysis: AnalysisResult) -> DiagramPlan:
        nodes = [
            DiagramNode(
                id="node-array",
                label="整列済み配列",
                kind="data_structure",
                description="探索対象の配列",
                group="search_range",
                state=NodeState(active=True),
                visual=NodeVisual(shape="rectangle", emphasis="medium"),
            ),
            DiagramNode(
                id="node-left",
                label="left",
                kind="pointer",
                description="左端インデックス",
                group="search_range",
                state=NodeState(active=True, value="0"),
                visual=NodeVisual(shape="circle", emphasis="medium"),
            ),
            DiagramNode(
                id="node-mid",
                label="mid",
                kind="pointer",
                description="中央インデックス",
                group="search_range",
                state=NodeState(active=True),
                visual=NodeVisual(shape="circle", emphasis="high"),
            ),
            DiagramNode(
                id="node-right",
                label="right",
                kind="pointer",
                description="右端インデックス",
                group="search_range",
                state=NodeState(active=True, value="n-1"),
                visual=NodeVisual(shape="circle", emphasis="medium"),
            ),
        ]
        edges = [
            DiagramEdge(
                id="edge-1",
                from_node="node-left",
                to_node="node-mid",
                relation="calculate",
                label="中央を計算",
                directed=True,
            ),
            DiagramEdge(
                id="edge-2",
                from_node="node-mid",
                to_node="node-right",
                relation="updates",
                label="比較して範囲を更新",
                directed=True,
            ),
        ]
        annotations = [
            DiagramAnnotation(
                id="ann-1",
                text="整列済み配列が前提",
                target_ids=["node-array"],
                priority="high",
            )
        ]
        return DiagramPlan(
            topic="二分探索",
            diagram_type=analysis.diagram_type or "array_state_transition",
            summary="中央要素との比較で探索範囲を狭める手順",
            nodes=nodes,
            edges=edges,
            annotations=annotations,
            layout=LayoutHint(
                direction="left_to_right",
                grouping=[GroupingItem(group_id="search_range", label="探索範囲")],
                preferred_aspect_ratio="16:9",
            ),
            source=SourceInfo(
                session_id=analysis.session_id,
                utterance_id=analysis.utterance_id,
                source_text=text,
            ),
        )

    def _build_generic_process_plan(self, text: str, analysis: AnalysisResult) -> DiagramPlan:
        sentences = [seg.strip() for seg in re.split(r"[。.!?]\s*", text) if seg.strip()]
        if not sentences:
            sentences = [text.strip() or "説明内容"]
        steps = sentences[:4]

        nodes: list[DiagramNode] = []
        edges: list[DiagramEdge] = []

        for index, step in enumerate(steps):
            node_id = f"node-step-{index + 1}"
            nodes.append(
                DiagramNode(
                    id=node_id,
                    label=f"Step {index + 1}",
                    kind="process_step",
                    description=step,
                    group="flow",
                    state=NodeState(active=True),
                    visual=NodeVisual(shape="rectangle", emphasis="high" if index == 0 else "medium"),
                )
            )
            if index > 0:
                edges.append(
                    DiagramEdge(
                        id=f"edge-{index}",
                        from_node=f"node-step-{index}",
                        to_node=node_id,
                        relation="transitions_to",
                        label="next",
                        directed=True,
                    )
                )

        topic = self._extract_topic(text)
        return DiagramPlan(
            topic=topic,
            diagram_type=analysis.diagram_type or "process_flow",
            summary=f"{topic} の説明フロー",
            nodes=nodes,
            edges=edges,
            annotations=[],
            layout=LayoutHint(
                direction="left_to_right",
                grouping=[GroupingItem(group_id="flow", label="説明手順")],
                preferred_aspect_ratio="16:9",
            ),
            source=SourceInfo(
                session_id=analysis.session_id,
                utterance_id=analysis.utterance_id,
                source_text=text,
            ),
        )

    def _extract_topic(self, text: str) -> str:
        match = re.search(r"(配列|スタック|キュー|木|ポインタ|ループ|再帰|二分探索)", text)
        if match:
            return match.group(1)
        return "プログラミング説明"
