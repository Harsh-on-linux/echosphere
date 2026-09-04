"""Agent env validation + managed-OpenAI wiring (SDK session monkeypatched)."""
import asyncio
import sys

import pytest


def _fresh_agent_module():
    sys.modules.pop("agent", None)
    import agent

    return agent


@pytest.mark.parametrize("missing", ["AGORA_APP_ID", "AGORA_APP_CERTIFICATE"])
def test_agent_requires_env(fake_env, monkeypatch, missing):
    monkeypatch.delenv(missing, raising=False)
    agent = _fresh_agent_module()
    with pytest.raises(ValueError):
        agent.Agent()


def test_agent_constructs_with_full_env(fake_env):
    agent = _fresh_agent_module()
    instance = agent.Agent()
    assert instance.app_id == "0123456789abcdef0123456789abcdef"
    assert instance.client is not None


def test_start_wires_managed_openai_and_returns_shape(fake_env, monkeypatch):
    agent = _fresh_agent_module()
    captured = {}

    class FakeSession:
        async def start(self):
            return "test-agent-id"

        async def stop(self):
            captured["stopped"] = True

    def fake_create_async_session(self, **kwargs):
        captured["llm"] = self.llm
        captured["channel"] = kwargs.get("channel")
        captured["remote_uids"] = kwargs.get("remote_uids")
        return FakeSession()

    from agora_agent.agentkit import Agent as AgoraAgent

    monkeypatch.setattr(AgoraAgent, "create_async_session", fake_create_async_session)

    instance = agent.Agent()
    result = asyncio.run(instance.start(channel_name="ch", agent_uid=111, user_uid=222))

    assert result["agent_id"] == "test-agent-id"
    assert result["channel_name"] == "ch"
    assert result["status"] == "started"
    # Phase 4.1: voice routing info rides along (defaults: managed English)
    assert result["language"] == "en-IN"
    assert result["stt"] == "deepgram" and result["tts"] == "minimax"
    # The LLM stage is the managed OpenAI vendor (gpt-4o-mini), NOT CustomLLM.
    assert captured["llm"]["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["llm"]["params"]["model"] == "gpt-4o-mini"
    assert captured["llm"]["style"] == "openai"
    assert "vendor" not in captured["llm"]  # managed OpenAI has no custom vendor key
    assert captured["channel"] == "ch"
    assert captured["remote_uids"] == ["222"]


def test_start_wires_weathergpt_voice_loop(fake_env, monkeypatch):
    """Phase 2.1: WeatherGPT prompt, greeting, idle_timeout 120, interruption."""
    agent = _fresh_agent_module()
    captured = {}

    class FakeSession:
        async def start(self):
            return "test-agent-id"

        async def stop(self):
            captured["stopped"] = True

    def fake_create_async_session(self, **kwargs):
        captured["config"] = self.config
        captured["idle_timeout"] = kwargs.get("idle_timeout")
        captured["name"] = kwargs.get("name")
        captured["channel"] = kwargs.get("channel")
        captured["remote_uids"] = kwargs.get("remote_uids")
        return FakeSession()

    from agora_agent.agentkit import Agent as AgoraAgent

    monkeypatch.setattr(AgoraAgent, "create_async_session", fake_create_async_session)

    instance = agent.Agent()
    result = asyncio.run(instance.start(channel_name="ch", agent_uid=111, user_uid=222))

    assert result["agent_id"] == "test-agent-id"
    config = captured["config"]
    # WeatherGPT identity (not the Ada quickstart default)
    assert "WeatherGPT" in (config["instructions"] or "")
    assert "IMD" in (config["instructions"] or "")
    assert config["greeting"] == agent.WEATHERGPT_GREETING
    assert "IMD" in (config["failure_message"] or "")
    assert config["max_history"] == 10
    # Managed English loop: turn_detection en-US + voice interruption on
    turn_detection = config["turn_detection"]
    language = turn_detection.get("language") if isinstance(turn_detection, dict) else getattr(turn_detection, "language", None)
    assert language == "en-US"
    assert turn_detection["mode"] == "default"
    assert turn_detection["config"] == {
        "speech_threshold": 0.5,
        "start_of_speech": {
            "mode": "vad",
            "vad_config": {
                "interrupt_threshold": 0.5,
                "prefix_padding_ms": 250,
            },
        },
        "end_of_speech": {
            "mode": "vad",
            "vad_config": {
                "silence_duration_ms": 700,
                "pause_state_enabled": True,
            },
        },
    }
    interruption = config["interruption"]
    enabled = interruption.get("enable") if isinstance(interruption, dict) else getattr(interruption, "enable", None)
    assert enabled is True
    assert interruption["mode"] == "start_of_speech"
    assert config["advanced_features"].get("enable_sal") is None
    assert config.get("sal") is None
    # Free-tier guard: 2 min idle timeout, wx- session names
    assert captured["idle_timeout"] == 120
    assert str(captured["name"]).startswith("wx-")


def test_start_wires_opt_in_sal(fake_env, monkeypatch):
    """Phase 5.2: SAL is opt-in and sent through the SDK sal field."""
    agent = _fresh_agent_module()
    monkeypatch.setenv("SAL_ENABLED", "true")
    monkeypatch.setenv("SAL_SAMPLE_URL", "https://example.com/sal.wav")
    captured = {}

    class FakeSession:
        async def start(self):
            return "test-agent-id"

    def fake_create_async_session(self, **kwargs):
        captured["config"] = self.config
        return FakeSession()

    from agora_agent.agentkit import Agent as AgoraAgent
    monkeypatch.setattr(AgoraAgent, "create_async_session", fake_create_async_session)

    instance = agent.Agent()
    asyncio.run(instance.start(channel_name="ch", agent_uid=111, user_uid=222))

    config = captured["config"]
    assert config["advanced_features"]["enable_sal"] is True
    sal = config["sal"]
    assert sal.sal_mode == "locking"
    assert sal.sample_urls == {"default": "https://example.com/sal.wav"}


def test_interrupt_history_turns_passthrough(fake_env, monkeypatch):
    """Phase 2.2/2.3: interrupt + history/turns reach the active session."""
    agent = _fresh_agent_module()

    class FakeSession:
        def __init__(self):
            self.calls = []

        async def start(self):
            return "agent-abc"

        async def stop(self):
            pass

        async def interrupt(self):
            self.calls.append("interrupt")

        async def get_history(self):
            self.calls.append("history")
            return {"contents": []}

        async def get_turns(self, **kwargs):
            self.calls.append(("turns", kwargs))
            return {"turns": []}

    session = FakeSession()
    from agora_agent.agentkit import Agent as AgoraAgent

    monkeypatch.setattr(AgoraAgent, "create_async_session", lambda self, **k: session)
    instance = agent.Agent()
    asyncio.run(instance.start(channel_name="ch", agent_uid=111, user_uid=222))

    asyncio.run(instance.interrupt("agent-abc"))
    assert "interrupt" in session.calls
    assert asyncio.run(instance.get_history("agent-abc")) == {"contents": []}
    assert asyncio.run(instance.get_turns("agent-abc", page_index=1)) == {"turns": []}

    with pytest.raises(ValueError):
        asyncio.run(instance.interrupt("unknown-id"))
    with pytest.raises(ValueError):
        asyncio.run(instance.get_history("unknown-id"))
    with pytest.raises(ValueError):
        asyncio.run(instance.get_turns("unknown-id"))


def test_start_validates_arguments(fake_env, monkeypatch):
    agent = _fresh_agent_module()
    from agora_agent.agentkit import Agent as AgoraAgent

    monkeypatch.setattr(AgoraAgent, "create_async_session", lambda self, **k: None)
    instance = agent.Agent()
    with pytest.raises(ValueError):
        asyncio.run(instance.start(channel_name="", agent_uid=1, user_uid=2))
    with pytest.raises(ValueError):
        asyncio.run(instance.start(channel_name="c", agent_uid=0, user_uid=2))


def test_stop_uses_active_session_then_falls_back(fake_env, monkeypatch):
    agent = _fresh_agent_module()

    class FakeSession:
        def __init__(self):
            self.stopped = False

        async def start(self):
            return "agent-xyz"

        async def stop(self):
            self.stopped = True

    session = FakeSession()
    from agora_agent.agentkit import Agent as AgoraAgent

    monkeypatch.setattr(AgoraAgent, "create_async_session", lambda self, **k: session)
    instance = agent.Agent()

    fallback_calls = []

    async def fake_stop_agent(agent_id):
        fallback_calls.append(agent_id)

    monkeypatch.setattr(instance.client, "stop_agent", fake_stop_agent)

    asyncio.run(instance.start(channel_name="ch", agent_uid=111, user_uid=222))
    asyncio.run(instance.stop("agent-xyz"))
    assert session.stopped is True
    assert fallback_calls == []

    asyncio.run(instance.stop("unknown-id"))
    assert fallback_calls == ["unknown-id"]
