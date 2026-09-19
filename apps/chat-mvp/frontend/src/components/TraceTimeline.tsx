import type { TimelineEvent } from "../types";

interface TraceTimelineProps {
  events: TimelineEvent[];
}

function rowLabel(event: TimelineEvent): string {
  if (event.kind === "trace") {
    return "trace";
  }
  return event.span_type ?? "span";
}

function badgeClass(event: TimelineEvent): string {
  if (event.status === "error") {
    return "trace-timeline__badge trace-timeline__badge--error";
  }
  return `trace-timeline__badge trace-timeline__badge--${rowLabel(event)}`;
}

/** Renders one turn's Galileo trace (a `ChatResponse.timeline`, built by the
 * backend's `app/timeline.py` from the same trace/span events GalileoTracer
 * sends to Galileo) as a small nested tree with plain-English commentary —
 * a "what just got logged, and where" companion to the real dashboard. */
export function TraceTimeline({ events }: TraceTimelineProps) {
  if (events.length === 0) {
    return null;
  }

  return (
    <details className="trace-timeline">
      <summary className="trace-timeline__summary">Galileo trace ({events.length} spans)</summary>
      <ol className="trace-timeline__list">
        {events.map((event, index) => (
          <li
            key={index}
            className="trace-timeline__row"
            style={{ marginLeft: `calc(var(--b4g-space-md) * ${event.depth})` }}
          >
            <div className="trace-timeline__row-head">
              <span className={badgeClass(event)}>{rowLabel(event)}</span>
              <span className="trace-timeline__name">{event.name}</span>
              <span className="trace-timeline__meta">
                +{event.offset_ms}ms
                {event.duration_ms !== null ? ` · ${event.duration_ms}ms` : ""}
              </span>
            </div>
            <p className="trace-timeline__commentary">{event.commentary}</p>
          </li>
        ))}
      </ol>
    </details>
  );
}
