"""Phase 2.2 tests: ICAR/KVK Agro-Advisory decision engine."""
import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import pytest
import agro_advisory


def _sse_json(text):
    for line in text.splitlines():
        if line.startswith("data: "):
            return json.loads(line[len("data: "):])
    raise AssertionError(f"no SSE data payload in: {text[:500]}")


@pytest.mark.asyncio
async def test_cotton_heavy_rain_advisory():
    advisory = await agro_advisory.evaluate_agro_advisory(
        crop="cotton",
        district_or_location="Nagpur",
        rainfall_mm=45.0,
        growth_stage="flowering",
    )
    assert advisory["status"] == "success"
    assert advisory["spraying_advisable"] is False
    assert any("waterlog" in w.lower() or "heavy rain" in w.lower() for w in advisory["warnings"])
    assert any("drainage" in a.lower() for a in advisory["recommended_actions"])


@pytest.mark.asyncio
async def test_onion_blight_risk_high_humidity():
    advisory = await agro_advisory.evaluate_agro_advisory(
        crop="onion",
        district_or_location="Nashik",
        rainfall_mm=0.0,
        humidity_percent=88.0,
        temp_max=28.0,
        temp_min=20.0,
    )
    assert advisory["status"] == "success"
    assert any("purple blotch" in w.lower() or "fungal" in w.lower() for w in advisory["warnings"])


@pytest.mark.asyncio
async def test_gusty_winds_postpone_spraying():
    advisory = await agro_advisory.evaluate_agro_advisory(
        crop="paddy",
        district_or_location="Thanjavur",
        rainfall_mm=0.0,
        wind_kmh=36.0,
    )
    assert advisory["spraying_advisable"] is False
    assert any("wind" in w.lower() for w in advisory["warnings"])


def test_mcp_exposes_agro_tool(client):
    with client as c:
        r = c.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            headers={"Accept": "application/json, text/event-stream"},
        )
    assert r.status_code == 200
    payload = _sse_json(r.text)
    tool_names = {t["name"] for t in payload["result"]["tools"]}
    assert "get_crop_weather_advisory" in tool_names
