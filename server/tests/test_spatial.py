"""Phase 3.4: spatial reasoning + fallbacks (plan.md 3.4 deliverable)."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import pytest
import location_resolver
import imd_client

# Plan.md 3.4 deliverable: 10 informal names resolve correctly.
TABLE = [
    ("Mumbai", "533"),
    ("Bombay", "533"),
    ("Mum-bai", "533"),
    ("Thane Creek", "535"),
    ("Puna", "528"),
    ("Madras", "441"),
    ("Chennai area", "441"),
    ("Tanjore", "211"),
    ("Nagai", "468"),
    ("Rameshwaram", "453"),
]

@pytest.mark.parametrize("spoken,expected", TABLE)
def test_informal_names_table(spoken, expected):
    r = location_resolver.fuzzy_match(spoken)
    assert r["district_id"] == expected, f"{spoken!r} -> {r}"


def test_fallback_low_confidence_has_nearest_latlon():
    r = location_resolver.resolve_with_fallback("My small village Xyzqwe")
    assert r["district_id"] is None
    assert len(r["candidates"]) <= 3
    assert r["fallback"]["strategy"] == "clarify_then_latlon"
    nearest = r["fallback"]["nearest"]
    assert nearest is not None
    assert isinstance(nearest["lat"], float) and isinstance(nearest["lon"], float)


def test_fallback_resolved_has_no_fallback():
    r = location_resolver.resolve_with_fallback("Pune")
    assert r["district_id"] == "528"
    assert r["fallback"] is None


def test_fallback_state_hint_for_statewide_query():
    r = location_resolver.resolve_with_fallback("Maharashtra")
    assert r["state_hint"] == "Maharashtra"


@pytest.mark.asyncio
async def test_subdivision_warning_mock():
    imd_client.clear_cache()
    data = await imd_client.get_subdivision_warning("Maharashtra")
    assert data["status"] == "success"
    assert "data" in data


@pytest.mark.asyncio
async def test_forecast_for_location_resolved():
    imd_client.clear_cache()
    data = await imd_client.get_forecast_for_location("Pune")
    assert data["status"] == "success"
    assert data["resolution"]["district_id"] == "528"


@pytest.mark.asyncio
async def test_forecast_for_location_unknown_uses_latlon():
    imd_client.clear_cache()
    data = await imd_client.get_forecast_for_location("My small village Xyzqwe")
    assert data["status"] == "success"
    assert data["_fallback_used"] == "latlon"
    assert data["resolution"]["district_id"] is None
