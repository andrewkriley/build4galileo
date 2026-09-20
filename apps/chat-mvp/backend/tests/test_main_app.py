"""Boots the real FastAPI app (including its lifespan, which spawns the demo
MCP server subprocess) and checks `/config` and `/chat`'s auth-gate — no
network calls, no API keys needed."""

from app.main import app
from fastapi.testclient import TestClient


def test_config_reports_no_providers_without_keys(monkeypatch) -> None:
    for var in (
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "VLLM_BASE_URL",
        "OLLAMA_BASE_URL",
    ):
        monkeypatch.delenv(var, raising=False)

    with TestClient(app) as client:
        response = client.get("/config")

    assert response.status_code == 200
    body = response.json()
    assert body["available_providers"] == []
    assert body["models"] == {}


def test_config_reports_a_local_provider_once_its_base_url_is_set(monkeypatch) -> None:
    for var in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.setenv("VLLM_BASE_URL", "http://localhost:8000/v1")

    with TestClient(app) as client:
        response = client.get("/config")

    body = response.json()
    assert body["available_providers"] == ["vllm"]
    # No real vLLM server is running in tests, so the live /v1/models fetch
    # fails and the provider is offered with an empty model list rather
    # than erroring the whole /config call.
    assert body["models"] == {"vllm": []}


def test_chat_rejects_a_provider_with_no_key(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with TestClient(app) as client:
        response = client.post(
            "/chat", json={"message": "hi", "session_id": "s1", "provider": "anthropic"}
        )

    assert response.status_code == 400
