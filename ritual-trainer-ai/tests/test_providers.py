"""Offline provider dispatch tests: no real API keys or network requests."""
from unittest.mock import Mock

import pytest

import ritual_coach as coach


def fake_reply(data, status=200):
    reply = Mock(status_code=status, ok=(status == 200))
    reply.json.return_value = data
    reply.headers = {"content-type": "application/json"}
    reply.text = "test response"
    return reply


def test_gemini_uses_free_provider_and_same_persona(monkeypatch):
    request = Mock(return_value=fake_reply({"candidates": [{"content": {"parts": [{"text": "Detailed coaching report."}]}}]}))
    monkeypatch.setattr(coach.requests, "post", request)
    text = coach.generate_report("Gemini (free tier)", "test-key", "gemini-3.8-flash", {"team": "The Hidden King"},
                                 {"available": False}, [], "Hard Carry", "Balanced improvement", {})
    assert text == "Detailed coaching report."
    args, kwargs = request.call_args
    assert "generativelanguage.googleapis.com" in args[0]
    assert kwargs["headers"]["x-goog-api-key"] == "test-key"
    assert "FEW_SHOT" not in kwargs["json"]["systemInstruction"]["parts"][0]["text"]
    assert "EXAMPLE 1" in kwargs["json"]["systemInstruction"]["parts"][0]["text"]
    assert "The Hidden King" in kwargs["json"]["contents"][0]["parts"][0]["text"]


def test_ollama_uses_local_server_with_no_key(monkeypatch):
    request = Mock(return_value=fake_reply({"message": {"content": "Local coaching answer."}}))
    monkeypatch.setattr(coach.requests, "post", request)
    monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
    result = coach.ask_followup("Ollama (local, offline)", "", "gemma3:4b", "How do I farm?", "Initial report", {},
                                {"available": False}, [], "Support & Utility", "Farming", {})
    assert result == "Local coaching answer."
    assert request.call_args.args[0] == "http://localhost:11434/api/chat"
    assert request.call_args.kwargs["json"]["stream"] is False
    assert "How do I farm?" in request.call_args.kwargs["json"]["messages"][1]["content"]


def test_provider_ready_flags():
    assert coach.provider_ready("Ollama (local, offline)", "")
    assert not coach.provider_ready("Gemini (free tier)", "")
    assert coach.provider_ready("Gemini (free tier)", "some-key")
    with pytest.raises(ValueError):
        coach.default_model("OpenAI")


def test_free_tier_limit_is_clear(monkeypatch):
    monkeypatch.setattr(coach.requests, "post", Mock(return_value=fake_reply({"error": {"message": "Quota"}}, status=429)))
    with pytest.raises(RuntimeError, match="free-tier request limit"):
        coach._ai_request("Gemini (free tier)", "test-key", "gemini-3.8-flash", "rules", "prompt", 800)


def test_unknown_provider_not_sent_anywhere(monkeypatch):
    request = Mock()
    monkeypatch.setattr(coach.requests, "post", request)
    with pytest.raises(ValueError, match="Unknown provider"):
        coach._ai_request("OpenAI", "", "gpt-4.1-mini", "rules", "prompt", 800)
    request.assert_not_called()


def test_default_gemini_model_is_current(monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    assert coach.default_model("Gemini (free tier)") == "gemini-3.8-flash"


def test_old_model_error_explains_404(monkeypatch):
    error = {"error": {"message": "This model models/gemini-2.5-flash is no longer available to new users."}}
    request = Mock(return_value=fake_reply(error, status=404))
    monkeypatch.setattr(coach.requests, "post", request)
    with pytest.raises(RuntimeError, match="change AI model to gemini-3.8-flash"):
        coach._ai_request("Gemini (free tier)", "test-key", "gemini-2.5-flash", "rules", "prompt", 800)


def test_current_gemini_model_generate_content_endpoint(monkeypatch):
    request = Mock(return_value=fake_reply({"candidates": [{"content": {"parts": [{"text": "Coaching OK"}]}}]}))
    monkeypatch.setattr(coach.requests, "post", request)
    assert coach._ai_request("Gemini (free tier)", "test-key", "gemini-3.8-flash", "rules", "prompt", 800) == "Coaching OK"
    assert request.call_args.args[0].endswith("/models/gemini-3.8-flash:generateContent")
