from typing import Protocol

from app.schemas.analysis import DomainDecision, VisualizationDecision


class LLMProvider(Protocol):
    provider_name: str

    async def normalize_text(self, text: str) -> str:
        ...

    async def classify_domain(self, text: str) -> DomainDecision:
        ...

    async def decide_visualization(self, text: str) -> VisualizationDecision:
        ...
