from app.schemas.analysis import DomainDecision
from app.services.llm.provider_base import LLMProvider


class DomainFilterService:
    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    async def classify(self, normalized_text: str) -> DomainDecision:
        return await self._provider.classify_domain(normalized_text)
