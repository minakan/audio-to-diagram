from app.schemas.websocket import AudioChunkEvent


class VADService:
    def is_speech(self, chunk: AudioChunkEvent) -> bool:
        return chunk.vad_state == "speech"
