"""Shared fixtures for the server test suite.

Standalone: no Agora cloud, no real credentials. A deterministic fake env is
injected, and python-dotenv is neutralized so a developer's real `server/.env`
cannot override the test env (server.py loads it with override=True).
"""
import importlib
import os
import sys

import pytest

# Make `import server` / `import agent` resolve to server/src/*.
_SERVER_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if _SERVER_SRC not in sys.path:
    sys.path.insert(0, _SERVER_SRC)

FAKE_ENV = {
    "AGORA_APP_ID": "0123456789abcdef0123456789abcdef",
    "AGORA_APP_CERTIFICATE": "fedcba9876543210fedcba9876543210",
}


@pytest.fixture
def fake_env(monkeypatch):
    """Inject a deterministic env and stop dotenv from clobbering it."""
    import dotenv

    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: False)
    for key, value in FAKE_ENV.items():
        monkeypatch.setenv(key, value)
    return dict(FAKE_ENV)


class FakeAgent:
    """Stand-in for the real Agent (mirrors scripts/run_fake_server.py)."""

    def __init__(self):
        self.started = []
        self.stopped = []
        self.interrupted = []
        self.history_calls = []
        self.turns_calls = []
        # Phase 6.3: PSTN Beta gate — flip in tests to exercise the dial path.
        self.telephony_enabled = False
        self.dial_calls = []
        self.hangup_calls = []

    async def start(self, channel_name, agent_uid, user_uid, output_audio_codec=None,
                    language=None, persona=None):
        self.started.append((channel_name, agent_uid, user_uid, output_audio_codec,
                             language, persona))
        return {
            "agent_id": f"fake-agent-{agent_uid}",
            "channel_name": channel_name,
            "status": "started",
        }

    async def stop(self, agent_id):
        self.stopped.append(agent_id)

    async def interrupt(self, agent_id):
        if agent_id == "unknown-id":
            raise ValueError(f"unknown agent_id: {agent_id}")
        self.interrupted.append(agent_id)

    async def get_history(self, agent_id):
        if agent_id == "unknown-id":
            raise ValueError(f"unknown agent_id: {agent_id}")
        self.history_calls.append(agent_id)
        return {"contents": []}

    async def get_turns(self, agent_id, page_index=None, page_size=None):
        if agent_id == "unknown-id":
            raise ValueError(f"unknown agent_id: {agent_id}")
        self.turns_calls.append((agent_id, page_index, page_size))
        return {"turns": [], "page_index": page_index}

    def telephony_status(self):
        return {"enabled": self.telephony_enabled, "mode": "fake"}

    async def dial_call(self, to_number, from_number=None, language=None, persona=None):
        import agent as agent_module

        to = agent_module.parse_e164_number(to_number, "toNumber")
        if from_number is not None:
            agent_module.parse_e164_number(from_number, "fromNumber")
        if not self.telephony_enabled:
            raise agent_module.TelephonyDisabledError(agent_module.TELEPHONY_SETUP_GUIDE)
        self.dial_calls.append((to, from_number, language, persona))
        return {"agent_id": "fake-tel-1", "channel_name": "tel-ch", "to_number": to, "status": "calling"}

    async def hangup_call(self, agent_id):
        import agent as agent_module

        if not self.telephony_enabled:
            raise agent_module.TelephonyDisabledError(agent_module.TELEPHONY_SETUP_GUIDE)
        if agent_id == "unknown-id":
            raise ValueError(f"unknown agent_id: {agent_id}")
        self.hangup_calls.append(agent_id)


@pytest.fixture
def server_module(fake_env):
    """Import server.py fresh, with the fake env + neutralized dotenv applied."""
    sys.modules.pop("server", None)
    sys.modules.pop("agent", None)
    import server

    importlib.reload(server)
    return server


@pytest.fixture
def client(server_module):
    """A FastAPI TestClient whose agent is a FakeAgent (no cloud)."""
    from fastapi.testclient import TestClient

    fake = FakeAgent()
    server_module.agent = fake
    test_client = TestClient(server_module.app)
    test_client.fake_agent = fake
    return test_client
