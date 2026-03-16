import base64
import logging
from collections.abc import Sequence
from typing import Any

from app.core.config import Settings
from app.schemas.websocket import AudioChunkEvent

logger = logging.getLogger(__name__)

_async_openai_client_cls: Any | None

try:
    from openai import AsyncOpenAI as _loaded_async_openai_client_cls
except Exception:  # pragma: no cover
    _async_openai_client_cls = None
else:
    _async_openai_client_cls = _loaded_async_openai_client_cls


class STTService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: Any | None = (
            _async_openai_client_cls(api_key=settings.openai_api_key)
            if settings.openai_api_key and _async_openai_client_cls is not None
            else None
        )

    async def transcribe_partial(self, chunk: AudioChunkEvent) -> str:
        if chunk.debug_text:
            return chunk.debug_text
        return "音声を解析中..."

    async def transcribe_final(self, chunks: Sequence[AudioChunkEvent]) -> str:
        debug_texts = [chunk.debug_text.strip() for chunk in chunks if chunk.debug_text and chunk.debug_text.strip()]
        if debug_texts:
            # Keep semantic hint stable even if the same debug text was attached to every chunk.
            deduped: list[str] = []
            for text in debug_texts:
                if text not in deduped:
                    deduped.append(text)
            return " ".join(deduped)

        if self._client is not None:
            audio_bytes = self._concat_audio(chunks)
            if audio_bytes:
                try:
                    transcript = await self._client.audio.transcriptions.create(
                        model=self._settings.openai_stt_model,
                        file=("utterance.webm", audio_bytes, "audio/webm"),
                    )
                    text = getattr(transcript, "text", "").strip()
                    if text:
                        return text
                except Exception as exc:  # pragma: no cover
                    logger.warning("OpenAI STT failed, using fallback transcript: %s", exc)

        return "配列の探索手順を説明しています。"

    def _concat_audio(self, chunks: Sequence[AudioChunkEvent]) -> bytes:
        data = bytearray()
        for chunk in chunks:
            try:
                data.extend(base64.b64decode(chunk.audio_base64))
            except Exception:
                continue
        return bytes(data)
