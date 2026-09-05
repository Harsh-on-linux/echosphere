# -*- coding: utf-8 -*-
"""
Tests for Phase 6: Regional Weather Audio Bulletin Pre-Synthesis & Cache
Verifies multilingual bulletin generation, TTL caching, FastMCP tool integration,
and FastAPI endpoint.
"""
import json
import pytest

from bulletin_cache import (
    clear_bulletin_cache,
    generate_bulletin_script,
    get_or_create_cached_bulletin,
)


def _sse_json(text: str) -> dict:
    """Extract JSON-RPC payload from SSE response."""
    for line in text.splitlines():
        if line.startswith("data: "):
            return json.loads(line[len("data: "):])
    raise AssertionError(f"no SSE payload: {text[:500]}")


@pytest.fixture(autouse=True)
def clean_cache():
    clear_bulletin_cache()
    yield
    clear_bulletin_cache()


def test_generate_bulletin_script_multilingual():
    # Hindi
    script_hi = generate_bulletin_script(
        district_name="Nashik",
        language="hi-IN",
        persona="farmer",
        weather_data={"temp_c": 30.0, "weather_desc": "धूप", "rain_prob_pct": 10},
    )
    assert "Nashik" in script_hi
    assert "30.0" in script_hi
    assert "कीटनाशक छिड़काव" in script_hi

    # Marathi
    script_mr = generate_bulletin_script(
        district_name="Pune",
        language="mr-IN",
        persona="farmer",
        weather_data={"temp_c": 28.5, "weather_desc": "ढगाळ", "rain_prob_pct": 80},
    )
    assert "Pune" in script_mr
    assert "औषध फवारणी" in script_mr
    assert "स्थगित रखें" in script_mr or "सल्ला" in script_mr

    # English
    script_en = generate_bulletin_script(
        district_name="Nagpur",
        language="en-IN",
        persona="farmer",
        weather_data={"temp_c": 35.0, "weather_desc": "Hot", "rain_prob_pct": 5},
    )
    assert "Nagpur" in script_en
    assert "35.0°C" in script_en


def test_bulletin_caching_and_hit():
    # First call: cache miss
    b1 = get_or_create_cached_bulletin(district_name="Amravati", language="hi-IN")
    assert b1["cache_hit"] is False
    assert b1["audio_codec"] == "opus"
    assert "amravati" in b1["audio_url"].lower()

    # Second call: cache hit
    b2 = get_or_create_cached_bulletin(district_name="Amravati", language="hi-IN")
    assert b2["cache_hit"] is True
    assert b2["cache_key"] == b1["cache_key"]
    assert b2["script"] == b1["script"]


def test_regional_bulletin_api_endpoint(client):
    with client as c:
        res = c.get("/api/regionalBulletin?district=Nashik&language=mr-IN&persona=farmer")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["district"] == "Nashik"
        assert data["language"] == "mr-IN"
        assert "audio_url" in data
        assert len(data["script"]) > 20


def test_mcp_regional_bulletin_tool(client):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "get_regional_weather_bulletin",
            "arguments": {"district_name": "Kolhapur", "language": "mr-IN"},
        },
    }
    with client as c:
        resp = c.post(
            "/mcp",
            json=payload,
            headers={"Accept": "application/json, text/event-stream"},
        )
        assert resp.status_code == 200
        data = _sse_json(resp.text)
        assert data["result"]["isError"] is False
        assert "Kolhapur" in resp.text
