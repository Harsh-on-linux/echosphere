"""Phase 1.2 tests: Open-Meteo secondary meteorological fallback and circuit breaker."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import pytest
import respx
import httpx
from openmeteo_client import get_openmeteo_forecast, clear_openmeteo_cache, WMO_CODES
import imd_client
from mcp_server import get_mcp


SAMPLE_OPENMETEO_RESPONSE = {
    "latitude": 18.52,
    "longitude": 73.86,
    "timezone": "Asia/Kolkata",
    "daily": {
        "time": ["2026-09-05", "2026-09-06", "2026-09-07"],
        "weather_code": [0, 61, 95],
        "temperature_2m_max": [30.5, 28.2, 27.0],
        "temperature_2m_min": [22.1, 21.5, 20.8],
        "precipitation_sum": [0.0, 12.4, 35.0],
        "precipitation_probability_max": [10, 85, 95],
        "wind_speed_10m_max": [14.2, 24.5, 38.0]
    }
}


@pytest.mark.asyncio
@respx.mock
async def test_openmeteo_live_get():
    clear_openmeteo_cache()
    route = respx.get("https://api.open-meteo.com/v1/forecast").respond(
        status_code=200, json=SAMPLE_OPENMETEO_RESPONSE
    )
    result = await get_openmeteo_forecast(18.5204, 73.8567)
    assert route.called
    assert result["status"] == "success"
    assert "Open-Meteo" in result["source"]
    assert len(result["forecast_days"]) == 3
    day0 = result["forecast_days"][0]
    assert day0["weather_desc"] == "Clear sky"
    assert day0["temp_max"] == 30.5
    day1 = result["forecast_days"][1]
    assert day1["weather_desc"] == "Slight rain"
    assert day1["rainfall_mm"] == 12.4


@pytest.mark.asyncio
@respx.mock
async def test_imd_client_live_fallback_bridge():
    clear_openmeteo_cache()
    respx.get("https://api.open-meteo.com/v1/forecast").respond(
        status_code=200, json=SAMPLE_OPENMETEO_RESPONSE
    )
    data = await imd_client.get_live_fallback_forecast(18.52, 73.86)
    assert data["status"] == "success"
    assert "Open-Meteo" in data["source"]
    assert len(data["forecast_days"]) == 3


@pytest.mark.asyncio
@respx.mock
async def test_openmeteo_handles_http_error_gracefully():
    clear_openmeteo_cache()
    respx.get("https://api.open-meteo.com/v1/forecast").respond(status_code=503)
    result = await get_openmeteo_forecast(18.52, 73.86)
    assert result["status"] == "fallback_error"
    assert "temporarily unavailable" in result["message"]


def _sse_json(text):
    for line in text.splitlines():
        if line.startswith("data: "):
            import json
            return json.loads(line[len("data: "):])
    raise AssertionError(f"no SSE data payload in: {text[:500]}")


def test_mcp_exposes_openmeteo_tool(client):
    with client as c:
        r = c.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            headers={"Accept": "application/json, text/event-stream"},
        )
    assert r.status_code == 200
    payload = _sse_json(r.text)
    names = {t["name"] for t in payload["result"]["tools"]}
    assert "get_openmeteo_forecast" in names
