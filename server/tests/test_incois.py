"""Phase 2.1 tests: INCOIS Marine & Ocean State Forecast Integration."""
import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import pytest
import incois_client


def _sse_json(text):
    for line in text.splitlines():
        if line.startswith("data: "):
            return json.loads(line[len("data: "):])
    raise AssertionError(f"no SSE data payload in: {text[:500]}")


@pytest.mark.asyncio
async def test_incois_ocean_state_forecast_nagapattinam():
    incois_client.clear_incois_cache()
    data = await incois_client.get_ocean_state_forecast("Nagapattinam")
    assert data["status"] == "success"
    assert "INCOIS" in data["source"]
    assert data["wave_height_meters"] == 1.8
    assert data["sea_condition"] == "Moderate"
    assert "craft_safety" not in data or data["vessel_safety_advisory"]
    assert "kattumaram" in data["vessel_safety_advisory"]["traditional_kattumaram"].lower() or "caution" in data["vessel_safety_advisory"]["traditional_kattumaram"].lower()


@pytest.mark.asyncio
async def test_incois_high_wave_alert_puri_rough():
    incois_client.clear_incois_cache()
    data = await incois_client.get_high_wave_alert("Puri")
    assert data["status"] == "success"
    assert data["alert_level"] in ("ORANGE", "RED")
    assert "caution" in data["warning_text"].lower() or "danger" in data["warning_text"].lower()


@pytest.mark.asyncio
async def test_incois_pfz_rameswaram():
    incois_client.clear_incois_cache()
    data = await incois_client.get_potential_fishing_zone("Rameswaram")
    assert data["status"] == "success"
    assert data["landing_center"] == "Pamban"
    assert data["distance_km"] == 18
    assert data["bearing_degrees"] == 140
    assert "depth_meters" in data


def test_mcp_exposes_incois_tools(client):
    with client as c:
        r = c.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            headers={"Accept": "application/json, text/event-stream"},
        )
    assert r.status_code == 200
    payload = _sse_json(r.text)
    tool_names = {t["name"] for t in payload["result"]["tools"]}
    assert "get_ocean_state_forecast" in tool_names
    assert "get_high_wave_alert" in tool_names
    assert "get_potential_fishing_zone" in tool_names
