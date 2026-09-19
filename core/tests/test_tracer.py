from helpers import RecordingTracer


def test_nested_spans_get_correct_parent_ids() -> None:
    tracer = RecordingTracer()
    session = tracer.start_session("s1")

    with tracer.trace(session, name="turn", input="hi") as trace:
        with trace.span("agent", "supervisor", input="hi") as sup:
            with sup.span("agent", "worker", input="hi") as worker:
                with worker.span("llm", "anthropic", input="hi") as llm:
                    llm.set_output("done")
                worker.set_output("done")
            sup.set_output("done")
        trace.set_output("done")

    spans = {span.name: span for span in tracer.span_starts()}
    assert spans["supervisor"].parent_span_id is None
    assert spans["worker"].parent_span_id == spans["supervisor"].id
    assert spans["anthropic"].parent_span_id == spans["worker"].id
    assert spans["anthropic"].trace_id == spans["supervisor"].trace_id


def test_exception_inside_span_marks_it_errored_and_propagates() -> None:
    tracer = RecordingTracer()
    session = tracer.start_session("s1")

    with tracer.trace(session, name="turn", input="hi") as trace:
        try:
            with trace.span("tool", "flaky", input={}) as span:
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        trace.set_output("recovered")

    (span,) = [s for s in tracer.span_starts() if s.name == "flaky"]
    assert span.status == "error"
    assert "boom" in (span.error or "")
