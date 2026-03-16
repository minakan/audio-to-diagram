from app.schemas.analysis import DomainDecision, VisualizationDecision
from app.schemas.common import DomainLabel
from app.services.llm.provider_base import LLMProvider


class VisualizationDecisionService:
    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    async def decide(
        self,
        normalized_text: str,
        domain_decision: DomainDecision,
    ) -> VisualizationDecision:
        if domain_decision.label != DomainLabel.PROGRAMMING:
            return VisualizationDecision(
                needed=False,
                reason="domain_irrelevant",
                diagram_type=None,
            )
        return await self._provider.decide_visualization(normalized_text)
