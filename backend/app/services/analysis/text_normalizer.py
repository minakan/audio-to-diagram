from app.services.llm.provider_base import LLMProvider


class TextNormalizer:
    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    async def normalize(self, text: str) -> str:
        return await self._provider.normalize_text(text)
