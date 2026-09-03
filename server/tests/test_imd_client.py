"""Tests for imd_client with mock fallback (TTL 300s)."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import pytest
import imd_client

@pytest.mark.asyncio
async def test_city_forecast_mock():
    imd_client.clear_cache()
    data = await imd_client.get_city_forecast_7d("528")
    assert data["status"] == "success"
    assert "data" in data
    assert data["source"] is not None

@pytest.mark.asyncio
async def test_district_nowcast_mock_and_cached():
    imd_client.clear_cache()
    d1 = await imd_client.get_district_nowcast("528")
    d2 = await imd_client.get_district_nowcast("528")
    # second call should be cached (same object or equal)
    assert d1 == d2
    assert imd_client.cache_info()["size"] >= 1

@pytest.mark.asyncio
async def test_fishermen_warning_mock():
    imd_client.clear_cache()
    data = await imd_client.get_fishermen_warning("468")
    assert data["status"] == "success"

@pytest.mark.asyncio
async def test_cyclone_track_mock():
    imd_client.clear_cache()
    data = await imd_client.get_cyclone_track()
    assert "data" in data
    assert data["data"][0]["cyclone_name"] == "MOCK-01"

@pytest.mark.asyncio
async def test_cache_ttl_value():
    info = imd_client.cache_info()
    assert info["ttl"] == 300
    assert info["use_mock"] is True

@pytest.mark.asyncio
async def test_latlon_fallback():
    imd_client.clear_cache()
    data = await imd_client.get_city_forecast_latlon(18.52, 73.85)
    assert data["status"] == "success"
