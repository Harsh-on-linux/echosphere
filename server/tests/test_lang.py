"""Phase 4.1: Indic pipeline — Sarvam BYOK with managed fallback (plan.md 4.1)."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import pytest
import persona_prompt


@pytest.mark.parametrize("raw,expected", [
    (None, "en-IN"), ("", "en-IN"), ("en-IN", "en-IN"), ("en", "en-IN"),
    ("hi", "hi-IN"), ("hi-IN", "hi-IN"), ("Hindi", "hi-IN"),
    ("ta", "ta-IN"), ("tamil", "ta-IN"), ("mr", "mr-IN"), ("marathi", "mr-IN"),
    ("bn", "bn-IN"), ("bangla", "bn-IN"), ("auto", "auto"),
    ("xx-YY", "en-IN"),
])
def test_normalize_language(raw, expected):
    assert persona_prompt.normalize_language(raw) == expected


@pytest.mark.parametrize("lang", ["en-IN", "hi-IN", "ta-IN", "mr-IN", "bn-IN"])
def test_greeting_per_language(lang):
    assert persona_prompt.get_greeting(lang) == persona_prompt.GREETINGS[lang]


def _start(fake_env, monkeypatch, **kwargs):
    sys.modules.pop("agent", None)
    import agent as agent_mod
    captured = {}

    class FakeSession:
        async def start(self):
            return "test-agent-id"

    def fake_create_async_session(self, **kwargs_):
        captured["llm"] = self.llm
        captured["stt"] = self.stt
        captured["tts"] = self.tts
        captured["config"] = self.config
        captured["kwargs"] = kwargs_
        return FakeSession()

    from agora_agent.agentkit import Agent as AgoraAgent
    monkeypatch.setattr(AgoraAgent, "create_async_session", fake_create_async_session)
    instance = agent_mod.Agent()
    result = asyncio.run(instance.start(channel_name="ch", agent_uid=111, user_uid=222, **kwargs))
    return agent_mod, captured, result


def test_default_is_managed_english(fake_env, monkeypatch):
    monkeypatch.delenv("SARVAM_API_KEY", raising=False)
    agent_mod, captured, result = _start(fake_env, monkeypatch)
    assert result["language"] == "en-IN"
    assert result["stt"] == "deepgram" and result["tts"] == "minimax"
    assert captured["stt"]["vendor"] == "deepgram"  # BYOK-less managed path
    assert captured["config"]["turn_detection"]["language"] == "en-US"
    assert captured["config"]["greeting"] == persona_prompt.GREETINGS["en-IN"]


def test_hindi_with_key_uses_sarvam(fake_env, monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "test-key")
    agent_mod, captured, result = _start(fake_env, monkeypatch, language="hi-IN")
    assert result["language"] == "hi-IN"
    assert result["stt"] == "sarvam" and result["tts"] == "sarvam"
    assert captured["stt"] == {"vendor": "sarvam",
                               "params": {"api_key": "test-key", "language": "hi-IN"}}
    assert captured["tts"]["vendor"] == "sarvam"
    assert captured["tts"]["params"]["target_language_code"] == "hi-IN"
    assert captured["tts"]["params"]["speaker"] == "anushka"
    assert captured["config"]["turn_detection"]["language"] == "hi-IN"
    assert captured["config"]["greeting"] == persona_prompt.GREETINGS["hi-IN"]
    # LLM stays managed gpt-4o-mini (BYOK only for speech)
    assert captured["llm"]["params"]["model"] == "gpt-4o-mini"


def test_indic_without_key_falls_back_to_managed(fake_env, monkeypatch):
    monkeypatch.delenv("SARVAM_API_KEY", raising=False)
    agent_mod, captured, result = _start(fake_env, monkeypatch, language="ta-IN")
    assert result["stt"] == "deepgram" and result["tts"] == "minimax"
    # Greeting still follows the requested language
    assert captured["config"]["greeting"] == persona_prompt.GREETINGS["ta-IN"]


def test_auto_uses_unknown_stt(fake_env, monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "test-key")
    agent_mod, captured, result = _start(fake_env, monkeypatch, language="auto")
    assert result["language"] == "auto"
    assert captured["stt"]["params"]["language"] == "unknown"
    assert captured["tts"]["params"]["target_language_code"] == "en-IN"


def test_english_with_sarvam_voice_activates_sarvam(fake_env, monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "test-key")
    agent_mod, captured, result = _start(fake_env, monkeypatch, language="en-IN", voice="anushka")
    assert result["stt"] == "sarvam" and result["tts"] == "sarvam"
    assert captured["tts"]["params"]["speaker"] == "anushka"
    assert captured["tts"]["params"]["target_language_code"] == "en-IN"

