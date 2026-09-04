"""Phase 4.2: persona-aware prompt + tool routing + TTS rate (plan.md 4.2)."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import pytest
import persona_prompt


@pytest.mark.parametrize("text,expected", [
    ("Is it safe to go fishing from Nagapattinam tomorrow?", "fisherman"),
    ("sea boat machli samudra", "fisherman"),
    ("Pune me kal barish hogi kya sowing se pehle?", "farmer"),
    ("crop khet fasal beej harvest", "farmer"),
    ("Cyclone track for Odisha?", "disaster"),
    ("storm toofan flood alert", "disaster"),
    ("cyclone warning for fishermen in Rameswaram", "disaster"),
    ("Hello, what is the weather in Pune?", "general"),
    ("", "general"),
    (None, "general"),
])
def test_detect_persona(text, expected):
    assert persona_prompt.detect_persona(text) == expected


@pytest.mark.parametrize("raw,expected", [
    (None, "general"), ("", "general"), ("farmer", "farmer"),
    ("FARMER", "farmer"), ("fisherman", "fisherman"), ("disaster", "disaster"),
    ("general", "general"), ("astronaut", "general"),
])
def test_normalize_persona(raw, expected):
    assert persona_prompt.normalize_persona(raw) == expected


def test_system_prompt_routes_tools_per_persona():
    assert "fishermen_warning" in persona_prompt.get_system_prompt("fisherman")
    assert "sea_area_bulletin" in persona_prompt.get_system_prompt("fisherman")
    assert "agromet" in persona_prompt.get_system_prompt("farmer")
    assert "districtrainfall" in persona_prompt.get_system_prompt("farmer")
    assert "cyclone_track" in persona_prompt.get_system_prompt("disaster")
    # Same location, different persona -> different routing (plan.md 4.2 demo)
    assert (persona_prompt.get_system_prompt("farmer")
            != persona_prompt.get_system_prompt("fisherman"))


def _start(fake_env, monkeypatch, **kwargs):
    sys.modules.pop("agent", None)
    import agent as agent_mod
    captured = {}

    class FakeSession:
        async def start(self):
            return "test-agent-id"

    def fake_create_async_session(self, **kwargs_):
        captured["llm"] = self.llm
        captured["tts"] = self.tts
        captured["config"] = self.config
        return FakeSession()

    from agora_agent.agentkit import Agent as AgoraAgent
    monkeypatch.setattr(AgoraAgent, "create_async_session", fake_create_async_session)
    instance = agent_mod.Agent()
    result = asyncio.run(instance.start(channel_name="ch", agent_uid=111, user_uid=222, **kwargs))
    return agent_mod, captured, result


def test_farmer_persona_slows_tts_for_elders(fake_env, monkeypatch):
    monkeypatch.delenv("SARVAM_API_KEY", raising=False)
    agent_mod, captured, result = _start(fake_env, monkeypatch, persona="farmer")
    assert result["persona"] == "farmer"
    assert "agromet" in captured["config"]["instructions"]
    voice_setting = captured["tts"]["params"]["voice_setting"]
    assert voice_setting["speed"] == 0.9


def test_fisherman_sarvam_uses_persona_rate_and_hint(fake_env, monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "test-key")
    agent_mod, captured, result = _start(
        fake_env, monkeypatch, persona="fisherman", language="ta-IN")
    assert result["persona"] == "fisherman"
    assert result["language"] == "ta-IN"
    assert "fishermen_warning" in captured["config"]["instructions"]
    assert captured["tts"]["params"]["pace"] == 1.0
    assert captured["tts"]["params"]["target_language_code"] == "ta-IN"


def test_unknown_persona_maps_to_general(fake_env, monkeypatch):
    agent_mod, captured, result = _start(fake_env, monkeypatch, persona="astronaut")
    assert result["persona"] == "general"
    assert "Persona hint" not in captured["config"]["instructions"]
