from pydantic import BaseModel


class TranscriptPartial(BaseModel):
    session_id: str
    utterance_id: str
    text: str
    start_ms: int
    end_ms: int


class TranscriptFinal(BaseModel):
    session_id: str
    utterance_id: str
    text: str
    normalized_text: str
    start_ms: int
    end_ms: int
