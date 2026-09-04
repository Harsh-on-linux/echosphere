"""Phase 7.2: functional test matrix (plan.md 7.2).

Automates the offline half of each matrix row — persona detection,
location resolution, and the expected IMD tool chain in mock mode (every
fact carries IMD source + timestamp). Manual half (needs live audio):
- Noise row: play traffic/boat audio via
    ffmpeg -re -i traffic.wav -f s16le -ar 16000 -ac 1 - | <rtc-inject>
  and expect a correct transcript (built-in NS + opt-in SAL, Phase 5.2).
- Full voice rows: `bun run dev` -> Start conversation -> speak the input
  -> RTM history must show the same resolve -> tool sequence asserted here.
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import pytest

import imd_client
from location_resolver import fuzzy_match
from persona_prompt import detect_persona, normalize_language


def _assert_grounded(payload):
    """Every weather fact carries IMD source + timestamp (finale criterion)."""
    assert payload.get("source"), f"missing IMD source: {payload}"
    assert payload.get("cached_at"), f"missing IMD timestamp: {payload}"


@pytest.mark.asyncio
async def test_matrix_farmer_maharashtra_hindi():
    """'Pune me kal barish hogi kya sowing se pehle?' -> resolve + rainfall + agromet (hi-IN)."""
    utterance = "Pune me kal barish hogi kya sowing se pehle?"
    assert detect_persona(utterance) == "farmer"
    assert normalize_language("hi-IN") == "hi-IN"

    resolution = fuzzy_match("Pune")
    assert resolution["district_id"] == "528"
    assert resolution["state"] == "Maharashtra"

    rainfall = await imd_client.get_rainfall_stats(resolution["district_id"])
    agromet = await imd_client.get_agromet_advisory(resolution["district_id"])
    assert rainfall["status"] == "success"
    assert agromet["status"] == "success"
    _assert_grounded(rainfall)
    _assert_grounded(agromet)


@pytest.mark.asyncio
async def test_matrix_fisherman_tamil_nadu_tamil():
    """'Is it safe to go to sea tomorrow from Rameswaram?' -> resolve + fishermen_warning + sea_bulletin (ta-IN)."""
    utterance = "Is it safe to go to sea tomorrow from Rameswaram?"
    assert detect_persona(utterance) == "fisherman"
    assert normalize_language("ta-IN") == "ta-IN"

    resolution = fuzzy_match("Rameswaram")
    assert resolution["district_id"] == "453"
    assert resolution["coastal"] is True

    warning = await imd_client.get_fishermen_warning(resolution["district_id"])
    sea = await imd_client.get_sea_area_bulletin()
    assert warning["status"] == "success"
    assert sea["status"] == "success"
    _assert_grounded(warning)
    _assert_grounded(sea)


@pytest.mark.asyncio
async def test_matrix_disaster_odisha_english():
    """'Cyclone track for Odisha?' -> cyclone_track + wind (en-IN, state-wide, no district)."""
    utterance = "Cyclone track for Odisha?"
    assert detect_persona(utterance) == "disaster"

    track = await imd_client.get_cyclone_track()
    wind = await imd_client.get_cyclone_wind()
    assert track["data"][0]["cyclone_name"] == "MOCK-01"
    assert wind["status"] == "success"
    _assert_grounded(track)
    _assert_grounded(wind)


@pytest.mark.asyncio
async def test_matrix_invalid_place_clarifies_with_nearest_district():
    """'My small village X' -> no hallucinated district; clarification info +
    nearest lat/lon retry ride along (plan.md 3.4: clarify, then lat/lon)."""
    result = await imd_client.get_forecast_for_location("My small village Xyzzy")
    resolution = result["resolution"]
    assert resolution["district_id"] is None
    assert len(resolution["candidates"]) == 3
    assert "Did you mean" in resolution["message"]
    # Caller retried via the nearest candidate's lat/lon instead of failing.
    assert result["_fallback_used"] == "latlon"
    assert result["status"] == "success"
    _assert_grounded(result)


def test_matrix_interrupt_then_nagpur_requery(fake_env, monkeypatch):
    """Start forecast, 'Nahi, Nagpur ka batao' mid-speech -> interrupt + new resolve (hi-IN)."""
    sys.modules.pop("agent", None)
    import agent as agent_mod

    interrupted = []

    class FakeSession:
        def __init__(self, agent_id):
            self.agent_id = agent_id

        async def start(self):
            return self.agent_id

        async def stop(self):
            pass

        async def interrupt(self):
            interrupted.append(self.agent_id)

    sessions = [FakeSession("agent-pune"), FakeSession("agent-nagpur")]

    def fake_create_async_session(self, **kwargs):
        return sessions.pop(0)

    from agora_agent.agentkit import Agent as AgoraAgent
    monkeypatch.setattr(AgoraAgent, "create_async_session", fake_create_async_session)

    async def run():
        instance = agent_mod.Agent()
        first = await instance.start(channel_name="ch", agent_uid=111, user_uid=222, language="hi-IN")
        await instance.interrupt(first["agent_id"])  # judge says "Ruko!" mid-answer
        second = await instance.start(channel_name="ch", agent_uid=111, user_uid=222, language="hi-IN")
        return first, second

    first, second = asyncio.run(run())
    assert interrupted == ["agent-pune"]
    assert second["agent_id"] == "agent-nagpur"
    assert second["language"] == "hi-IN"
    # New turn resolves the NEW district, not the interrupted one.
    assert fuzzy_match("Nagpur")["district_id"] == "629"
    assert fuzzy_match("Nagpur")["district_id"] != fuzzy_match("Pune")["district_id"]


def test_matrix_noisy_fisherman_profile_requires_https_voiceprint(fake_env, monkeypatch):
    """Noise row guard: SAL stays fail-closed without a valid https voiceprint,
    so a misconfigured boat-engine profile can never lock onto noise."""
    sys.modules.pop("agent", None)
    import agent as agent_mod

    monkeypatch.setenv("SAL_ENABLED", "true")
    monkeypatch.setenv("SAL_SAMPLE_URL", "http://insecure.local/sal.wav")
    assert agent_mod.get_sal_config() is None

    monkeypatch.setenv("SAL_SAMPLE_URL", "https://example.com/fisherman.wav")
    config = agent_mod.get_sal_config()
    assert config == {"sal_mode": "locking", "sample_urls": {"default": "https://example.com/fisherman.wav"}}

    monkeypatch.delenv("SAL_ENABLED")
    assert agent_mod.get_sal_config() is None
