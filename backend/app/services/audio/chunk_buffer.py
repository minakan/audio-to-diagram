from dataclasses import dataclass, field

from app.schemas.websocket import AudioChunkEvent


@dataclass
class UtteranceBuffer:
    chunks: list[AudioChunkEvent] = field(default_factory=list)

    def add(self, chunk: AudioChunkEvent) -> None:
        self.chunks.append(chunk)

    def flush(self) -> list[AudioChunkEvent]:
        flushed = self.chunks.copy()
        self.chunks.clear()
        return flushed

    def total_duration_ms(self) -> int:
        return sum(chunk.duration_ms for chunk in self.chunks)

    def is_empty(self) -> bool:
        return not self.chunks
