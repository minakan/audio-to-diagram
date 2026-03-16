import os

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_audio_to_diagram.db")

from app.main import app  # noqa: E402


def _drain_events(ws, max_events: int = 30) -> list[dict]:
    events: list[dict] = []
    for _ in range(max_events):
        data = ws.receive_json()
        events.append(data)
        event_name = data.get("event")
        if event_name == "svg.result":
            break
        if event_name == "pipeline.status" and data.get("status") in {"skipped", "completed"}:
            break
    return events


def test_websocket_pipeline_returns_diagram_for_programming_text() -> None:
    with TestClient(app) as client:
        with client.websocket_connect("/ws/audio") as ws:
            ws.send_json(
                {
                    "event": "session.start",
                    "session_id": "sess-1",
                    "client_timestamp": "2026-03-17T23:00:00+09:00",
                    "audio": {"sample_rate": 16000, "channels": 1, "mime_type": "audio/webm"},
                }
            )
            ws.receive_json()  # ack

            ws.send_json(
                {
                    "event": "audio.chunk",
                    "session_id": "sess-1",
                    "chunk_id": "chunk-001",
                    "sequence_no": 1,
                    "is_final_chunk": False,
                    "audio_base64": "AA==",
                    "duration_ms": 300,
                    "vad_state": "speech",
                    "debug_text": "二分探索では中央要素を比較します。",
                }
            )
            ws.receive_json()  # ack
            ws.receive_json()  # buffering
            ws.receive_json()  # partial

            ws.send_json(
                {
                    "event": "utterance.flush",
                    "session_id": "sess-1",
                    "reason": "manual_flush",
                    "last_chunk_id": "chunk-001",
                }
            )

            events = _drain_events(ws)
            event_names = {event.get("event") for event in events}

            assert "transcript.final" in event_names
            assert "analysis.result" in event_names
            assert "diagram.plan" in event_names
            assert "svg.result" in event_names


def test_websocket_pipeline_skips_irrelevant_text() -> None:
    with TestClient(app) as client:
        with client.websocket_connect("/ws/audio") as ws:
            ws.send_json(
                {
                    "event": "session.start",
                    "session_id": "sess-2",
                    "client_timestamp": "2026-03-17T23:00:00+09:00",
                    "audio": {"sample_rate": 16000, "channels": 1, "mime_type": "audio/webm"},
                }
            )
            ws.receive_json()

            ws.send_json(
                {
                    "event": "audio.chunk",
                    "session_id": "sess-2",
                    "chunk_id": "chunk-201",
                    "sequence_no": 1,
                    "is_final_chunk": False,
                    "audio_base64": "AA==",
                    "duration_ms": 250,
                    "vad_state": "speech",
                    "debug_text": "今日は提出期限の連絡をします。",
                }
            )
            ws.receive_json()
            ws.receive_json()
            ws.receive_json()

            ws.send_json(
                {
                    "event": "utterance.flush",
                    "session_id": "sess-2",
                    "reason": "manual_flush",
                    "last_chunk_id": "chunk-201",
                }
            )

            events = _drain_events(ws)
            event_names = [event.get("event") for event in events]
            statuses = [event.get("status") for event in events if event.get("event") == "pipeline.status"]

            assert "analysis.result" in event_names
            assert "diagram.plan" not in event_names
            assert "svg.result" not in event_names
            assert "skipped" in statuses
