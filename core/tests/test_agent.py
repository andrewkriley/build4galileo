import asyncio

from b4g_core.agents.agent import Agent
from b4g_core.providers.base import ProviderResponse, ToolCall
from b4g_core.providers.fake_provider import FakeProvider
from helpers import RecordingTracer


def _span_id(tracer: RecordingTracer, name: str) -> str:
    return next(s.id for s in tracer.span_starts() if s.name == name)


def test_router_picks_child_and_leaf_answers_directly() -> None:
    tracer = RecordingTracer()
    session = tracer.start_session("s1")

    worker = Agent(
        name="system_worker",
        agent_type="react",
        provider=FakeProvider([ProviderResponse(text="host info here", model="fake-model")]),
    )
    supervisor = Agent(
        name="supervisor",
        agent_type="supervisor",
        route=lambda msg: "system",
        children={"system": worker},
    )

    with tracer.trace(session, name="turn", input="what host am I on?") as trace:
        result = asyncio.run(supervisor.run("what host am I on?", trace))
        trace.set_output(result)

    assert result == "host info here"
    by_name = {s.name: s.parent_span_id for s in tracer.span_starts()}
    assert by_name["supervisor"] is None
    assert by_name["classifier"] == _span_id(tracer, "supervisor")
    assert by_name["system_worker"] == _span_id(tracer, "supervisor")
    assert by_name["fake"] == _span_id(tracer, "system_worker")


def test_worker_calls_tool_then_answers() -> None:
    tracer = RecordingTracer()
    session = tracer.start_session("s1")
    calls: list[tuple[str, dict]] = []

    async def call_tool(name: str, arguments: dict) -> str:
        calls.append((name, arguments))
        return "42 files found"

    worker = Agent(
        name="files_worker",
        provider=FakeProvider(
            [
                ProviderResponse(
                    text="",
                    tool_calls=[ToolCall(id="1", name="file_search", arguments={"query": "*.py"})],
                    model="fake-model",
                ),
                ProviderResponse(text="Found 42 files.", model="fake-model"),
            ]
        ),
        mcp_tools=[{"name": "file_search", "description": "", "input_schema": {}}],
        call_tool=call_tool,
    )

    with tracer.trace(session, name="turn", input="find python files") as trace:
        result = asyncio.run(worker.run("find python files", trace))

    assert result == "Found 42 files."
    assert calls == [("file_search", {"query": "*.py"})]
    tool_spans = [s for s in tracer.span_starts() if s.span_type == "tool"]
    assert len(tool_spans) == 1
    assert tool_spans[0].name == "file_search"


def test_repeated_identical_tool_call_stops_early() -> None:
    tracer = RecordingTracer()
    session = tracer.start_session("s1")

    same_call = ToolCall(id="1", name="http_ping", arguments={"url": "http://x"})
    worker = Agent(
        name="network_worker",
        provider=FakeProvider(
            [
                ProviderResponse(text="", tool_calls=[same_call], model="fake-model"),
                ProviderResponse(text="", tool_calls=[same_call], model="fake-model"),
            ]
        ),
        mcp_tools=[{"name": "http_ping", "description": "", "input_schema": {}}],
        call_tool=lambda name, args: _async_result("pong"),
    )

    with tracer.trace(session, name="turn", input="ping x") as trace:
        result = asyncio.run(worker.run("ping x", trace))

    assert "repeated identical call" in result
    # only the first round's tool call should have actually run
    assert len([s for s in tracer.span_starts() if s.span_type == "tool"]) == 1


def test_round_cap_stops_a_stuck_loop() -> None:
    tracer = RecordingTracer()
    session = tracer.start_session("s1")

    def looping_call(name: str, arguments: dict):
        return _async_result("ok")

    script = [
        ProviderResponse(
            text="",
            tool_calls=[ToolCall(id=str(i), name="http_ping", arguments={"n": i})],
            model="fake-model",
        )
        for i in range(10)
    ]
    worker = Agent(
        name="network_worker",
        provider=FakeProvider(script),
        mcp_tools=[{"name": "http_ping", "description": "", "input_schema": {}}],
        call_tool=looping_call,
        max_rounds=3,
    )

    with tracer.trace(session, name="turn", input="ping forever") as trace:
        result = asyncio.run(worker.run("ping forever", trace))

    assert "tool-call limit" in result


async def _async_result(value: str) -> str:
    return value
