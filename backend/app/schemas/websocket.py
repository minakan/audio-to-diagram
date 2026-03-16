from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.schemas.common import DomainLabel, PipelineStatus
from app.schemas.diagram_plan import DiagramPlan


class AudioConfig(BaseModel):
    sample_rate: int = 16000
    channels: int = 1
    mime_type: str = "audio/webm"


class SessionStartEvent(BaseModel):
    event: Literal["session.start"]
    session_id: str
    client_timestamp: datetime
    audio: AudioConfig


class AudioChunkEvent(BaseModel):
    event: Literal["audio.chunk"]
    session_id: str
    chunk_id: str
    sequence_no: int
    is_final_chunk: bool = False
    audio_base64: str
    duration_ms: int
    vad_state: Literal["speech", "silence", "unknown"] = "unknown"
    debug_text: str | None = None


class UtteranceFlushEvent(BaseModel):
    event: Literal["utterance.flush"]
    session_id: str
    reason: Literal["silence_timeout", "max_duration", "manual_flush", "page_unload"]
    last_chunk_id: str | None = None


class SessionStopEvent(BaseModel):
    event: Literal["session.stop"]
    session_id: str


ClientEvent = Annotated[
    SessionStartEvent | AudioChunkEvent | UtteranceFlushEvent | SessionStopEvent,
    Field(discriminator="event"),
]


class AckEvent(BaseModel):
    event: Literal["ack"] = "ack"
    session_id: str
    received_chunk_id: str | None = None


class PipelineStatusEvent(BaseModel):
    event: Literal["pipeline.status"] = "pipeline.status"
    session_id: str
    utterance_id: str | None = None
    status: PipelineStatus


class TranscriptPartialEvent(BaseModel):
    event: Literal["transcript.partial"] = "transcript.partial"
    session_id: str
    utterance_id: str
    text: str
    start_ms: int
    end_ms: int


class TranscriptFinalEvent(BaseModel):
    event: Literal["transcript.final"] = "transcript.final"
    session_id: str
    utterance_id: str
    text: str
    normalized_text: str
    start_ms: int
    end_ms: int


class AnalysisResultEvent(BaseModel):
    event: Literal["analysis.result"] = "analysis.result"
    session_id: str
    utterance_id: str
    programming_relevance_score: float
    domain_label: DomainLabel
    visualization_needed: bool
    visualization_reason: str
    diagram_type: str | None = None


class DiagramPlanEvent(BaseModel):
    event: Literal["diagram.plan"] = "diagram.plan"
    session_id: str
    utterance_id: str
    diagram_plan: DiagramPlan


class SVGResultEvent(BaseModel):
    event: Literal["svg.result"] = "svg.result"
    session_id: str
    utterance_id: str
    diagram_id: str
    svg: str
    prompt_version: str = "svg_v1"


class ErrorEvent(BaseModel):
    event: Literal["error"] = "error"
    session_id: str | None = None
    code: str
    message: str
    recoverable: bool = True
