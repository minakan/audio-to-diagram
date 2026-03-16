export type ClientStatus = "idle" | "recording" | "processing" | "error";

export type ServerEvent =
  | AckEvent
  | TranscriptPartialEvent
  | TranscriptFinalEvent
  | AnalysisResultEvent
  | DiagramPlanEvent
  | SvgResultEvent
  | PipelineStatusEvent
  | ErrorEvent;

export type AckEvent = {
  event: "ack";
  session_id: string;
  received_chunk_id?: string | null;
};

export type TranscriptPartialEvent = {
  event: "transcript.partial";
  session_id: string;
  utterance_id: string;
  text: string;
  start_ms: number;
  end_ms: number;
};

export type TranscriptFinalEvent = {
  event: "transcript.final";
  session_id: string;
  utterance_id: string;
  text: string;
  normalized_text: string;
  start_ms: number;
  end_ms: number;
};

export type AnalysisResultEvent = {
  event: "analysis.result";
  session_id: string;
  utterance_id: string;
  programming_relevance_score: number;
  domain_label: "programming" | "irrelevant";
  visualization_needed: boolean;
  visualization_reason: string;
  diagram_type?: string | null;
};

export type DiagramPlanEvent = {
  event: "diagram.plan";
  session_id: string;
  utterance_id: string;
  diagram_plan: Record<string, unknown>;
};

export type SvgResultEvent = {
  event: "svg.result";
  session_id: string;
  utterance_id: string;
  diagram_id: string;
  svg: string;
  prompt_version: string;
};

export type PipelineStatusEvent = {
  event: "pipeline.status";
  session_id: string;
  utterance_id?: string | null;
  status:
    | "buffering"
    | "transcribing"
    | "analyzing"
    | "diagram_planning"
    | "generating_svg"
    | "completed"
    | "skipped"
    | "error";
};

export type ErrorEvent = {
  event: "error";
  session_id?: string | null;
  code: string;
  message: string;
  recoverable: boolean;
};
