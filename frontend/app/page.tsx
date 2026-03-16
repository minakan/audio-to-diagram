"use client";

import { useMemo, useRef, useState } from "react";

import type {
  AnalysisResultEvent,
  ClientStatus,
  DiagramPlanEvent,
  PipelineStatusEvent,
  ServerEvent,
  SvgResultEvent,
  TranscriptFinalEvent,
  TranscriptPartialEvent,
} from "@/types/ws";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/audio";

function createSessionId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `sess-${crypto.randomUUID()}`;
  }
  return `sess-${Date.now()}`;
}

async function blobToBase64(blob: Blob): Promise<string> {
  const buffer = await blob.arrayBuffer();
  let binary = "";
  const bytes = new Uint8Array(buffer);
  bytes.forEach((value) => {
    binary += String.fromCharCode(value);
  });
  return btoa(binary);
}

export default function Page() {
  const [status, setStatus] = useState<ClientStatus>("idle");
  const [sessionId, setSessionId] = useState<string>("");
  const [pipelineStatus, setPipelineStatus] = useState<string>("-");
  const [debugText, setDebugText] = useState<string>("二分探索では中央の要素を比較して探索範囲を狭めます。");
  const [partialTranscript, setPartialTranscript] = useState<string>("");
  const [finalTranscripts, setFinalTranscripts] = useState<TranscriptFinalEvent[]>([]);
  const [lastAnalysis, setLastAnalysis] = useState<AnalysisResultEvent | null>(null);
  const [lastPlan, setLastPlan] = useState<DiagramPlanEvent | null>(null);
  const [lastSvg, setLastSvg] = useState<SvgResultEvent | null>(null);
  const [events, setEvents] = useState<string[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const sequenceRef = useRef<number>(0);

  const canStart = status === "idle" || status === "error";
  const canControlSession = status === "recording" || status === "processing";

  const addEventLog = (line: string): void => {
    setEvents((prev) => [line, ...prev].slice(0, 60));
  };

  const handleServerEvent = (payload: string): void => {
    const event = JSON.parse(payload) as ServerEvent;
    addEventLog(`${new Date().toLocaleTimeString()} | ${event.event}`);

    switch (event.event) {
      case "transcript.partial": {
        const e = event as TranscriptPartialEvent;
        setPartialTranscript(e.text);
        return;
      }
      case "transcript.final": {
        const e = event as TranscriptFinalEvent;
        setFinalTranscripts((prev) => [e, ...prev].slice(0, 20));
        setPartialTranscript("");
        return;
      }
      case "analysis.result": {
        setLastAnalysis(event as AnalysisResultEvent);
        return;
      }
      case "diagram.plan": {
        setLastPlan(event as DiagramPlanEvent);
        return;
      }
      case "svg.result": {
        setLastSvg(event as SvgResultEvent);
        setStatus("recording");
        return;
      }
      case "pipeline.status": {
        const e = event as PipelineStatusEvent;
        setPipelineStatus(e.status);
        if (e.status === "error") {
          setStatus("error");
        } else if (e.status === "completed" || e.status === "skipped") {
          setStatus("recording");
        } else if (e.status !== "buffering") {
          setStatus("processing");
        }
        return;
      }
      case "error": {
        setStatus("error");
        return;
      }
      default:
        return;
    }
  };

  const start = async (): Promise<void> => {
    try {
      setStatus("processing");
      setEvents([]);
      setFinalTranscripts([]);
      setLastAnalysis(null);
      setLastPlan(null);
      setLastSvg(null);
      setPartialTranscript("");

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      const id = createSessionId();
      setSessionId(id);
      sequenceRef.current = 0;

      ws.onmessage = (message) => handleServerEvent(message.data as string);
      ws.onerror = () => {
        addEventLog("WebSocket error");
        setStatus("error");
      };
      ws.onclose = () => {
        addEventLog("WebSocket closed");
      };

      ws.onopen = () => {
        ws.send(
          JSON.stringify({
            event: "session.start",
            session_id: id,
            client_timestamp: new Date().toISOString(),
            audio: {
              sample_rate: 16000,
              channels: 1,
              mime_type: "audio/webm",
            },
          })
        );

        const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
        recorderRef.current = recorder;

        recorder.ondataavailable = async (blobEvent: BlobEvent) => {
          const chunk = blobEvent.data;
          if (!chunk || chunk.size === 0 || ws.readyState !== WebSocket.OPEN) {
            return;
          }
          sequenceRef.current += 1;
          const audioBase64 = await blobToBase64(chunk);
          ws.send(
            JSON.stringify({
              event: "audio.chunk",
              session_id: id,
              chunk_id: `chunk-${String(sequenceRef.current).padStart(5, "0")}`,
              sequence_no: sequenceRef.current,
              is_final_chunk: false,
              audio_base64: audioBase64,
              duration_ms: 200,
              vad_state: "speech",
              debug_text: debugText || undefined,
            })
          );
        };

        recorder.start(200);
        setStatus("recording");
      };
    } catch (error) {
      addEventLog(`Start failed: ${(error as Error).message}`);
      setStatus("error");
    }
  };

  const flushUtterance = (): void => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN || !sessionId) {
      return;
    }
    ws.send(
      JSON.stringify({
        event: "utterance.flush",
        session_id: sessionId,
        reason: "manual_flush",
      })
    );
  };

  const stop = (): void => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN && sessionId) {
      ws.send(
        JSON.stringify({
          event: "session.stop",
          session_id: sessionId,
        })
      );
    }

    recorderRef.current?.stop();
    recorderRef.current = null;

    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;

    wsRef.current?.close();
    wsRef.current = null;

    setStatus("idle");
    setPipelineStatus("-");
  };

  const analysisText = useMemo(() => {
    if (!lastAnalysis) {
      return "(まだありません)";
    }
    return JSON.stringify(lastAnalysis, null, 2);
  }, [lastAnalysis]);

  const planText = useMemo(() => {
    if (!lastPlan) {
      return "(まだありません)";
    }
    return JSON.stringify(lastPlan.diagram_plan, null, 2);
  }, [lastPlan]);

  return (
    <main>
      <h1>Audio-to-Diagram MVP</h1>
      <p>
        WS endpoint: <code>{WS_URL}</code>
      </p>

      <div className="grid">
        <section className="panel" style={{ display: "grid", gap: 12 }}>
          <h2>Session Control</h2>
          <p>
            Status: <strong>{status}</strong> / Pipeline: <strong>{pipelineStatus}</strong>
          </p>
          <p>
            Session ID: <code>{sessionId || "-"}</code>
          </p>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button className="primary" disabled={!canStart} onClick={start}>
              録音開始
            </button>
            <button className="secondary" disabled={!canControlSession} onClick={flushUtterance}>
              発話確定（flush）
            </button>
            <button className="danger" disabled={!canControlSession} onClick={stop}>
              録音停止
            </button>
          </div>

          <div>
            <h3>Debug Transcript Hint</h3>
            <textarea
              rows={5}
              value={debugText}
              onChange={(e) => setDebugText(e.target.value)}
              placeholder="STT未接続環境向け。ここに書いた文が解析対象になります。"
            />
          </div>

          <div>
            <h3>Partial Transcript</h3>
            <div className="panel" style={{ padding: 10 }}>
              {partialTranscript || "(なし)"}
            </div>
          </div>

          <div>
            <h3>Recent Events</h3>
            <div className="event-log">
              {events.length === 0 ? "(イベント待機中)" : events.join("\n")}
            </div>
          </div>
        </section>

        <section style={{ display: "grid", gap: 16 }}>
          <div className="panel">
            <h2>Latest SVG</h2>
            <div
              className="svg-stage"
              dangerouslySetInnerHTML={{
                __html: lastSvg?.svg || "<p style='padding:16px;color:#64748b'>SVGはまだありません</p>",
              }}
            />
          </div>

          <div className="panel">
            <h2>Latest Analysis</h2>
            <pre style={{ margin: 0, overflowX: "auto" }}>{analysisText}</pre>
          </div>

          <div className="panel">
            <h2>Latest Diagram Plan</h2>
            <pre style={{ margin: 0, overflowX: "auto", maxHeight: 280 }}>{planText}</pre>
          </div>

          <div className="panel">
            <h2>Transcript History</h2>
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {finalTranscripts.length === 0 ? (
                <li>(なし)</li>
              ) : (
                finalTranscripts.map((item) => (
                  <li key={`${item.utterance_id}-${item.end_ms}`}>
                    <strong>{item.utterance_id}</strong>: {item.normalized_text}
                  </li>
                ))
              )}
            </ul>
          </div>
        </section>
      </div>
    </main>
  );
}
