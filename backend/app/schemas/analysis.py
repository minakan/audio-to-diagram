from pydantic import BaseModel

from app.schemas.common import DomainLabel


class DomainDecision(BaseModel):
    score: float
    label: DomainLabel
    reason: str


class VisualizationDecision(BaseModel):
    needed: bool
    reason: str
    diagram_type: str | None = None


class AnalysisResult(BaseModel):
    session_id: str
    utterance_id: str
    programming_relevance_score: float
    domain_label: DomainLabel
    visualization_needed: bool
    visualization_reason: str
    diagram_type: str | None = None
