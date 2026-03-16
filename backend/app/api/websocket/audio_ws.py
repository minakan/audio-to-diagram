import json
import logging
from dataclasses import dataclass

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import TypeAdapter, ValidationError

from app.schemas.common import PipelineStatus
from app.schemas.websocket import (
    AckEvent,
    AnalysisResultEvent,
    AudioChunkEvent,
    ClientEvent,
    DiagramPlanEvent,
    ErrorEvent,
    PipelineStatusEvent,
    SessionStartEvent,
    SessionStopEvent,
    SVGResultEvent,
    TranscriptFinalEvent,
    TranscriptPartialEvent,
    UtteranceFlushEvent,
)
from app.services.audio.chunk_buffer import UtteranceBuffer
from app.services.audio.utterance_segmenter import UtteranceSegmenter
from app.services.orchestration.realtime_pipeline import RealtimePipeline
from app.services.storage.pipeline_logger import PipelineLogger
from app.services.stt.stt_service import STTService

logger = logging.getLogger(__name__)

router = APIRouter()
client_event_adapter = TypeAdapter(ClientEvent)


@dataclass
class ConnectionState:
    session_id: str | None = None
    utterance_index: int = 0


@router.websocket("/ws/audio")
async def audio_ws(websocket: WebSocket) -> None:
    await websocket.accept()

    state = ConnectionState()
    buffer = UtteranceBuffer()
    segmenter = UtteranceSegmenter(max_duration_ms=6000)

    pipeline: RealtimePipeline = websocket.app.state.realtime_pipeline
    stt_service: STTService = websocket.app.state.stt_service
    pipeline_logger: PipelineLogger = websocket.app.state.pipeline_logger

    try:
        while True:
            raw_payload = await websocket.receive_text()
            try:
                event = client_event_adapter.validate_python(json.loads(raw_payload))
            except (ValidationError, json.JSONDecodeError) as exc:
                await _send_error(websocket, None, "INVALID_EVENT", str(exc), recoverable=True)
                continue

            if isinstance(event, SessionStartEvent):
                state.session_id = event.session_id
                state.utterance_index = 0
                await pipeline_logger.start_session(event.session_id)
                await websocket.send_json(AckEvent(session_id=event.session_id).model_dump(mode="json"))
                continue

            if state.session_id is None:
                await _send_error(
                    websocket,
                    None,
                    "SESSION_NOT_STARTED",
                    "session.start must be sent before other events",
                    recoverable=True,
                )
                continue

            if event.session_id != state.session_id:
                await _send_error(
                    websocket,
                    state.session_id,
                    "SESSION_MISMATCH",
                    "event session_id does not match active session",
                    recoverable=True,
                )
                continue

            if isinstance(event, AudioChunkEvent):
                buffer.add(event)
                await pipeline_logger.log_chunk(
                    session_id=event.session_id,
                    chunk_id=event.chunk_id,
                    sequence_no=event.sequence_no,
                    duration_ms=event.duration_ms,
                    vad_state=event.vad_state,
                )
                await websocket.send_json(
                    AckEvent(
                        session_id=event.session_id,
                        received_chunk_id=event.chunk_id,
                    ).model_dump(mode="json")
                )
                await websocket.send_json(
                    PipelineStatusEvent(
                        session_id=event.session_id,
                        status=PipelineStatus.BUFFERING,
                    ).model_dump(mode="json")
                )

                partial_text = await stt_service.transcribe_partial(event)
                preview_utterance_id = f"utt-{state.utterance_index + 1:04d}"
                partial_end_ms = buffer.total_duration_ms()
                await websocket.send_json(
                    TranscriptPartialEvent(
                        session_id=event.session_id,
                        utterance_id=preview_utterance_id,
                        text=partial_text,
                        start_ms=0,
                        end_ms=partial_end_ms,
                    ).model_dump(mode="json")
                )

                if event.is_final_chunk or segmenter.should_force_flush(buffer):
                    await _flush_utterance(websocket, state, buffer, pipeline, reason="max_duration")
                continue

            if isinstance(event, UtteranceFlushEvent):
                await _flush_utterance(websocket, state, buffer, pipeline, reason=event.reason)
                continue

            if isinstance(event, SessionStopEvent):
                if not buffer.is_empty():
                    await _flush_utterance(websocket, state, buffer, pipeline, reason="manual_flush")
                await pipeline_logger.stop_session(event.session_id)
                await websocket.send_json(
                    PipelineStatusEvent(
                        session_id=event.session_id,
                        status=PipelineStatus.COMPLETED,
                    ).model_dump(mode="json")
                )
                await websocket.close()
                return

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected session=%s", state.session_id)
        if state.session_id:
            await pipeline_logger.stop_session(state.session_id)
    except Exception as exc:  # pragma: no cover
        logger.exception("Unhandled websocket error: %s", exc)
        await _send_error(websocket, state.session_id, "UNEXPECTED_ERROR", str(exc), recoverable=False)


async def _flush_utterance(
    websocket: WebSocket,
    state: ConnectionState,
    buffer: UtteranceBuffer,
    pipeline: RealtimePipeline,
    reason: str,
) -> None:
    if state.session_id is None or buffer.is_empty():
        return

    state.utterance_index += 1
    utterance_id = f"utt-{state.utterance_index:04d}"
    chunks = buffer.flush()

    await websocket.send_json(
        PipelineStatusEvent(
            session_id=state.session_id,
            utterance_id=utterance_id,
            status=PipelineStatus.TRANSCRIBING,
        ).model_dump(mode="json")
    )

    result = await pipeline.process_utterance(
        session_id=state.session_id,
        utterance_id=utterance_id,
        chunks=chunks,
    )

    final_end_ms = sum(chunk.duration_ms for chunk in chunks)
    await websocket.send_json(
        TranscriptFinalEvent(
            session_id=state.session_id,
            utterance_id=utterance_id,
            text=result.transcript_text,
            normalized_text=result.normalized_text,
            start_ms=0,
            end_ms=final_end_ms,
        ).model_dump(mode="json")
    )

    await websocket.send_json(
        PipelineStatusEvent(
            session_id=state.session_id,
            utterance_id=utterance_id,
            status=PipelineStatus.ANALYZING,
        ).model_dump(mode="json")
    )

    await websocket.send_json(
        AnalysisResultEvent(
            session_id=state.session_id,
            utterance_id=utterance_id,
            programming_relevance_score=result.analysis.programming_relevance_score,
            domain_label=result.analysis.domain_label,
            visualization_needed=result.analysis.visualization_needed,
            visualization_reason=result.analysis.visualization_reason,
            diagram_type=result.analysis.diagram_type,
        ).model_dump(mode="json")
    )

    if result.diagram_plan is None:
        await websocket.send_json(
            PipelineStatusEvent(
                session_id=state.session_id,
                utterance_id=utterance_id,
                status=PipelineStatus.SKIPPED,
            ).model_dump(mode="json")
        )
        return

    await websocket.send_json(
        PipelineStatusEvent(
            session_id=state.session_id,
            utterance_id=utterance_id,
            status=PipelineStatus.DIAGRAM_PLANNING,
        ).model_dump(mode="json")
    )

    await websocket.send_json(
        DiagramPlanEvent(
            session_id=state.session_id,
            utterance_id=utterance_id,
            diagram_plan=result.diagram_plan,
        ).model_dump(mode="json", by_alias=True)
    )

    if result.svg is None or result.diagram_id is None:
        await _send_error(
            websocket,
            state.session_id,
            "SVG_GENERATION_FAILED",
            f"svg generation failed for reason={reason}",
            recoverable=True,
        )
        await websocket.send_json(
            PipelineStatusEvent(
                session_id=state.session_id,
                utterance_id=utterance_id,
                status=PipelineStatus.SKIPPED,
            ).model_dump(mode="json")
        )
        return

    await websocket.send_json(
        PipelineStatusEvent(
            session_id=state.session_id,
            utterance_id=utterance_id,
            status=PipelineStatus.GENERATING_SVG,
        ).model_dump(mode="json")
    )

    await websocket.send_json(
        SVGResultEvent(
            session_id=state.session_id,
            utterance_id=utterance_id,
            diagram_id=result.diagram_id,
            svg=result.svg,
            prompt_version="svg_v1",
        ).model_dump(mode="json")
    )

    await websocket.send_json(
        PipelineStatusEvent(
            session_id=state.session_id,
            utterance_id=utterance_id,
            status=PipelineStatus.COMPLETED,
        ).model_dump(mode="json")
    )


async def _send_error(
    websocket: WebSocket,
    session_id: str | None,
    code: str,
    message: str,
    recoverable: bool,
) -> None:
    await websocket.send_json(
        ErrorEvent(
            session_id=session_id,
            code=code,
            message=message,
            recoverable=recoverable,
        ).model_dump(mode="json")
    )
