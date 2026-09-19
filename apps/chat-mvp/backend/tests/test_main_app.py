"""Boots the real FastAPI app (including its lifespan, which spawns the demo
MCP server subprocess) and checks `/config` and `/chat`'s auth-gate — no
network calls, no API keys needed."""

from app.main import app
from fastapi.testclient import TestClient


def test_config_reports_no_providers_without_keys(monkeypatch) -> None:
    for var in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(var, raising=False)

    with TestClient(app) as client:
        response = client.get("/config")

    assert response.status_code == 200
    assert response.json()["available_providers"] == []


def test_chat_rejects_a_provider_with_no_key(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with TestClient(app) as client:
        response = client.post(
            "/chat", json={"message": "hi", "session_id": "s1", "provider": "anthropic"}
        )

    assert response.status_code == 400
