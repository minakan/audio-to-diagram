import pytest

from app.schemas.analysis import AnalysisResult
from app.schemas.common import DomainLabel
from app.services.analysis.diagram_planner_service import DiagramPlannerService


@pytest.mark.asyncio
async def test_binary_search_plan_shape() -> None:
    planner = DiagramPlannerService()
    analysis = AnalysisResult(
        session_id="s1",
        utterance_id="u1",
        programming_relevance_score=0.95,
        domain_label=DomainLabel.PROGRAMMING,
        visualization_needed=True,
        visualization_reason="state transitions",
        diagram_type="array_state_transition",
    )

    plan = await planner.plan("二分探索では中央を比較して範囲を狭めます。", analysis)

    assert plan.topic == "二分探索"
    assert len(plan.nodes) >= 3
    assert len(plan.edges) >= 1
