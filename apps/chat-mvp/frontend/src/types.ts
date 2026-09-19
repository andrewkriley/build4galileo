export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  /** Only set on the assistant message that finished a turn — see
   * app/timeline.py on the backend for how this is built from the
   * turn's Galileo trace/spans. */
  timeline?: TimelineEvent[];
}

export type TimelineEventKind = "trace" | "span";
export type TimelineSpanType = "agent" | "llm" | "tool" | null;

export interface TimelineEvent {
  kind: TimelineEventKind;
  span_type: TimelineSpanType;
  icon: string;
  name: string | null;
  status: "ok" | "error";
  depth: number;
  offset_ms: number;
  duration_ms: number | null;
  commentary: string;
  input_preview: string;
  output_preview: string;
}
