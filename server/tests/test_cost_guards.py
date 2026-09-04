"""Phase 7.1: free-tier cost guards (plan.md 7.1).

Automated half of the cost-guard matrix — fails the build if a change burns
the free budget. Manual half (run before the finale):
1. Agora Console > Usage shows 0 lingering agents after idle kill.
2. No card on file — Agora suspends (not charges) past 300 Conv AI mins.
3. Sarvam dashboard still >Rs.50 after ~20 Indic test sessions.

Pricing refs: research.md #10 (Agora $0.10/min, 300 one-time free mins,
20 PCU/app) and #12 (Sarvam STT Rs.30/hr, TTS Rs.15-30/10k chars, Rs.100 free).
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import pytest

import imd_client

# --- Agora Conv AI budget (research.md #10) ---
MANAGED_USD_PER_MIN = 0.10
FREE_CONV_AI_MINS = 300
MAX_PCU = 20


def test_idle_timeout_constant_is_120():
    sys.modules.pop("agent", None)
    import agent as agent_mod

    assert agent_mod.WEATHERGPT_IDLE_TIMEOUT == 120


def test_ten_idle_sessions_all_carry_idle_timeout_and_stop_cleanly(fake_env, monkeypatch):
    """Unit half of '10 idle agents -> idle_timeout kills them'.

    Every session create carries idle_timeout=120 (server-side auto-leave
    after 2 min silence), and all 10 stop without lingering _sessions.
    """
    sys.modules.pop("agent", None)
    import agent as agent_mod

    created = []
    stopped = []

    class FakeSession:
        async def start(self):
            return f"agent-{len(created)}"

        async def stop(self):
            stopped.append(True)

    def fake_create_async_session(self, **kwargs):
        created.append(kwargs)
        return FakeSession()

    from agora_agent.agentkit import Agent as AgoraAgent
    monkeypatch.setattr(AgoraAgent, "create_async_session", fake_create_async_session)

    async def run():
        instance = agent_mod.Agent()
        ids = [
            await instance.start(channel_name=f"ch-{i}", agent_uid=100 + i, user_uid=200 + i)
            for i in range(10)
        ]
        assert len(created) == 10
        assert {c.get("idle_timeout") for c in created} == {120}
        assert all(str(c.get("name")).startswith("wx-") for c in created)
        for entry in ids:
            await instance.stop(entry["agent_id"])
        assert len(stopped) == 10
        assert instance._sessions == {}
        assert instance._telephony_ids == set()

    asyncio.run(run())


def test_full_idle_wave_burns_less_than_free_budget():
    """Worst case: all 20 PCU slots idle at once -> 20 x 120s = 40 min < 300."""
    worst_idle_mins = MAX_PCU * 120 / 60
    assert worst_idle_mins < FREE_CONV_AI_MINS


def test_demo_minute_budget_within_300_free():
    """Hackathon plan: dev 180 + rehearsal 50 + finale 5x5 = 255 min < 300."""
    planned = 180 + 50 + 5 * 5
    assert planned < FREE_CONV_AI_MINS
    assert planned * MANAGED_USD_PER_MIN == pytest.approx(25.5)  # $0 inside free quota


@pytest.mark.parametrize("lang", ["hi-IN", "ta-IN", "mr-IN", "bn-IN", "auto"])
def test_indic_langs_spend_nothing_without_sarvam_key(fake_env, monkeypatch, lang):
    """No SARVAM_API_KEY -> managed Deepgram/MiniMax for every language."""
    sys.modules.pop("agent", None)
    import agent as agent_mod

    monkeypatch.delenv("SARVAM_API_KEY", raising=False)

    class FakeSession:
        async def start(self):
            return "test-agent-id"

    def fake_create_async_session(self, **kwargs):
        return FakeSession()

    from agora_agent.agentkit import Agent as AgoraAgent
    monkeypatch.setattr(AgoraAgent, "create_async_session", fake_create_async_session)

    async def run():
        instance = agent_mod.Agent()
        return await instance.start(channel_name="ch", agent_uid=111, user_uid=222, language=lang)

    result = asyncio.run(run())
    assert result["stt"] == "deepgram" and result["tts"] == "minimax"


def test_sarvam_test_matrix_stt_cost_within_free_credit():
    """Plan.md 7.2 matrix: 6 voice tests x ~3 min = 18 min STT = Rs.9 << Rs.100."""
    matrix_sessions, mins_each = 6, 3
    stt_cost = matrix_sessions * mins_each / 60 * 30  # Rs.30/hr (research.md #12)
    assert stt_cost < 100


def test_reply_word_cap_bounds_tts_spend():
    """System prompt caps replies at <30 words, bounding Sarvam TTS chars.

    20 Indic sessions x 8 turns x 30 words x ~6 chars = ~29k chars, i.e.
    ~Rs.43 at the Rs.15/10k base rate — inside Rs.100 with STT (~Rs.30).
    """
    import persona_prompt

    assert "<30 words" in persona_prompt.WEATHERGPT_SYSTEM
    upper_chars = 20 * 8 * 30 * 6
    assert upper_chars * 15 / 10_000 < 100


@pytest.mark.asyncio
async def test_demo_script_makes_zero_http_calls_after_warmup():
    """10 mixed IMD queries (with repeats) -> billable HTTP stays 0 in mock
    mode, i.e. IMD calls are 0% of queries, well under the 30% target."""
    def boom():
        raise AssertionError("billable IMD HTTP call after warmup")

    imd_client.clear_cache()
    original = imd_client._get_client
    imd_client._get_client = boom
    try:
        queries = [
            imd_client.get_city_forecast_7d("528"),
            imd_client.get_district_nowcast("528"),
            imd_client.get_city_forecast_7d("528"),  # repeat -> cache
            imd_client.get_fishermen_warning("468"),
            imd_client.get_sea_area_bulletin(),
            imd_client.get_cyclone_track(),
            imd_client.get_cyclone_wind(),
            imd_client.get_cyclone_cou(),
            imd_client.get_district_nowcast("528"),  # repeat -> cache
            imd_client.get_forecast_for_location("Pune"),
        ]
        for coro in queries:
            data = await coro
            assert data.get("status") in ("success", "clarify")
        assert imd_client.cache_info()["size"] >= 5
    finally:
        imd_client._get_client = original


@pytest.mark.asyncio
async def test_live_path_caches_per_endpoint():
    """Same endpoint+params twice -> one network response reused (TTL 300s)."""
    calls = []

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            calls.append(1)
            return {"status": "success", "data": []}

    class FakeClient:
        async def get(self, url, params=None):
            return FakeResp()

    imd_client.clear_cache()
    original_client_factory, original_mock = imd_client._get_client, imd_client.USE_MOCK
    imd_client.USE_MOCK = False
    imd_client._get_client = lambda: FakeClient()
    try:
        # Call the endpoint twice with identical params: one network hit.
        await imd_client.get_city_forecast_7d("528")
        await imd_client.get_city_forecast_7d("528")
        assert len(calls) == 1
    finally:
        imd_client._get_client = original_client_factory
        imd_client.USE_MOCK = original_mock
