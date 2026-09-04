"""Phase 7.3: edge cases (plan.md 7.3).

- IMD down/timeout -> last cached (+timestamp), else mock + reason; voice
  layer offers retry via WEATHERGPT_FAILURE ("try again in a moment").
- Ambiguous location -> single stable clarification, never a loop.
- Rate limit -> bounded concurrency + backoff on 429/5xx; user hears the
  "Thoda samay dijiye" filler while the retry runs.
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import httpx
import pytest

import imd_client
from location_resolver import fuzzy_match


def _live_mode(monkeypatch):
    """Force the live path (no mock shortcut); each test installs its client."""
    monkeypatch.setattr(imd_client, "USE_MOCK", False)
    imd_client.clear_cache()
    return []


def _client(monkeypatch, handler):
    """Install a FakeClient driving `handler(url, params, calls)`."""
    calls = []

    async def get(self, url, params=None):
        return await handler(url, params, calls)

    monkeypatch.setattr(imd_client, "_get_client", lambda: type("C", (), {"get": get})())
    return calls


def _ok(payload):
    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return dict(payload)

    return FakeResp()


def _http_error(status):
    request = httpx.Request("GET", "https://api.imd.gov.in/api/v1/cityforecast")

    class FailResp:
        status_code = status

        def raise_for_status(self):
            raise httpx.HTTPStatusError(f"{status} limited", request=request,
                                        response=httpx.Response(status, request=request))

    return FailResp()


@pytest.mark.asyncio
async def test_outage_serves_last_good_stale_with_timestamp(monkeypatch):
    calls = _live_mode(monkeypatch)
    fresh = {"status": "success", "source": "live", "cached_at": "2026-01-01T00:00:00Z", "data": []}

    async def handler(url, params, calls):
        calls.append(1)
        if len(calls) == 1:
            return _ok(fresh)
        raise httpx.ConnectError("imd down")

    calls = _client(monkeypatch, handler)

    first = await imd_client.get_city_forecast_7d("528")
    assert first["source"] == "live"
    imd_client.cache.clear()  # TTL entry gone, last_good survives (outage memory)

    second = await imd_client.get_city_forecast_7d("528")
    assert second["_stale"] is True
    assert second["source"] == "live"  # last cached, not mock
    assert second["cached_at"] == "2026-01-01T00:00:00Z"
    assert "_fallback_reason" in second


@pytest.mark.asyncio
async def test_outage_cold_cache_falls_back_to_mock(monkeypatch):
    _live_mode(monkeypatch)

    async def handler(url, params, calls):
        raise httpx.ConnectError("imd down")

    _client(monkeypatch, handler)

    data = await imd_client.get_city_forecast_7d("528")
    assert data["status"] == "success"  # voice never breaks
    assert "_fallback_reason" in data


@pytest.mark.asyncio
async def test_transient_429_retried_then_succeeds(monkeypatch):
    calls = _live_mode(monkeypatch)

    async def handler(url, params, calls):
        calls.append(1)
        if len(calls) < 3:
            return _http_error(429)
        return _ok({"status": "success", "data": []})

    calls = _client(monkeypatch, handler)

    data = await imd_client.get_city_forecast_7d("528")
    assert data["status"] == "success"
    assert len(calls) == 3  # 1 try + 2 backoff retries


@pytest.mark.asyncio
async def test_burst_respects_concurrency_limiter(monkeypatch):
    _live_mode(monkeypatch)
    in_flight = {"current": 0, "max": 0}

    async def handler(url, params, calls):
        in_flight["current"] += 1
        in_flight["max"] = max(in_flight["max"], in_flight["current"])
        await asyncio.sleep(0.02)
        in_flight["current"] -= 1
        return _ok({"status": "success", "data": []})

    _client(monkeypatch, handler)

    # Distinct districts -> distinct cache keys -> all 8 hit the network path.
    results = await asyncio.gather(*[imd_client.get_city_forecast_7d(str(500 + i)) for i in range(8)])
    assert all(r["status"] == "success" for r in results)
    assert in_flight["max"] <= imd_client.MAX_IMD_CONCURRENCY
    assert in_flight["max"] > 1  # limiter shares, not serializes


def test_ambiguous_query_clarification_is_stable():
    """Same ambiguous query twice -> identical single clarification (no loop)."""
    first = fuzzy_match("Xyzzy village")
    second = fuzzy_match("Xyzzy village")
    assert first["district_id"] is None
    assert first["candidates"] == second["candidates"]
    assert first["message"] == second["message"]
    assert len(first["candidates"]) == 3


def test_rate_limit_filler_and_retry_offer_exist():
    """User-facing halves: queue filler + retry offer in the failure message."""
    import persona_prompt
    sys.modules.pop("agent", None)
    import agent as agent_mod

    assert any("Thoda samay dijiye" in phrase for phrase in persona_prompt.FILLER_PHRASES)
    assert "try again" in agent_mod.WEATHERGPT_FAILURE
