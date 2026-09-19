import pytest
from b4g_core.agents.tool_loop import RepeatedToolCall, ToolLoopGuard, ToolLoopLimitExceeded


def test_allows_distinct_calls() -> None:
    guard = ToolLoopGuard(max_rounds=5)
    guard.check("search", {"q": "a"})
    guard.check("search", {"q": "b"})  # different args, fine
    guard.check("ping", {"q": "a"})  # different tool, fine


def test_rejects_identical_repeated_call() -> None:
    guard = ToolLoopGuard(max_rounds=5)
    guard.check("search", {"q": "a"})
    with pytest.raises(RepeatedToolCall):
        guard.check("search", {"q": "a"})


def test_argument_order_does_not_matter() -> None:
    guard = ToolLoopGuard(max_rounds=5)
    guard.check("search", {"a": 1, "b": 2})
    with pytest.raises(RepeatedToolCall):
        guard.check("search", {"b": 2, "a": 1})


def test_round_cap() -> None:
    guard = ToolLoopGuard(max_rounds=2)
    guard.next_round()
    guard.next_round()
    with pytest.raises(ToolLoopLimitExceeded):
        guard.next_round()
