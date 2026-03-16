import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models import (
    AnalysisRecord,
    AudioChunkRecord,
    DiagramArtifactRecord,
    SessionRecord,
    TranscriptRecord,
)
from app.schemas.analysis import AnalysisResult
from app.schemas.diagram_plan import DiagramPlan

logger = logging.getLogger(__name__)


class PipelineLogger:
    def __init__(self, session_maker: async_sessionmaker) -> None:
        self._session_maker = session_maker

    async def start_session(self, session_id: str) -> None:
        async with self._session_maker() as session:
            existing = await session.scalar(select(SessionRecord).where(SessionRecord.session_id == session_id))
            if existing is not None:
                existing.status = "active"
                existing.ended_at = None
            else:
                session.add(SessionRecord(session_id=session_id, status="active"))
            await session.commit()

    async def stop_session(self, session_id: str) -> None:
        async with self._session_maker() as session:
            existing = await session.scalar(select(SessionRecord).where(SessionRecord.session_id == session_id))
            if existing is None:
                return
            existing.status = "stopped"
            existing.ended_at = datetime.now(UTC)
            await session.commit()

    async def log_chunk(
        self,
        *,
        session_id: str,
        chunk_id: str,
        sequence_no: int,
        duration_ms: int,
        vad_state: str,
    ) -> None:
        await self._safe_write(
            AudioChunkRecord(
                session_id=session_id,
                chunk_id=chunk_id,
                sequence_no=sequence_no,
                duration_ms=duration_ms,
                vad_state=vad_state,
            )
        )

    async def log_transcript(
        self,
        *,
        session_id: str,
        utterance_id: str,
        raw_text: str,
        normalized_text: str,
        start_ms: int,
        end_ms: int,
    ) -> None:
        await self._safe_write(
            TranscriptRecord(
                session_id=session_id,
                utterance_id=utterance_id,
                raw_text=raw_text,
                normalized_text=normalized_text,
                is_final=True,
                start_ms=start_ms,
                end_ms=end_ms,
            )
        )

    async def log_analysis(self, payload: AnalysisResult) -> None:
        await self._safe_write(
            AnalysisRecord(
                session_id=payload.session_id,
                utterance_id=payload.utterance_id,
                programming_relevance_score=payload.programming_relevance_score,
                domain_label=payload.domain_label,
                visualization_needed=payload.visualization_needed,
                visualization_reason=payload.visualization_reason,
                diagram_type=payload.diagram_type,
            )
        )

    async def log_diagram(
        self,
        *,
        diagram_id: str,
        plan: DiagramPlan,
        svg: str | None,
        provider: str,
        latency_ms: int,
        prompt_version: str = "svg_v1",
    ) -> None:
        await self._safe_write(
            DiagramArtifactRecord(
                diagram_id=diagram_id,
                session_id=plan.source.session_id,
                utterance_id=plan.source.utterance_id,
                diagram_plan=plan.model_dump(mode="json", by_alias=True),
                svg_content=svg,
                generation_prompt_version=prompt_version,
                provider=provider,
                latency_ms=latency_ms,
            )
        )

    async def _safe_write(self, record: object) -> None:
        try:
            async with self._session_maker() as session:
                session.add(record)
                await session.commit()
        except Exception as exc:
            logger.warning("logging skipped due to DB error: %s", exc)
