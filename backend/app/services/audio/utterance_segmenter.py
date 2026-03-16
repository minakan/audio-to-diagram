from app.services.audio.chunk_buffer import UtteranceBuffer


class UtteranceSegmenter:
    """Simple VAD-based segmenter for MVP."""

    def __init__(self, max_duration_ms: int = 6000) -> None:
        self.max_duration_ms = max_duration_ms

    def should_force_flush(self, buffer: UtteranceBuffer) -> bool:
        return buffer.total_duration_ms() >= self.max_duration_ms
