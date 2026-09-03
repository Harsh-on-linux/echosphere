# -*- coding: utf-8 -*-
"""
WeatherGPT IMD Client — Phase 1.2 + 3.1
Wraps 10 IMD endpoint groups with 5-minute TTL cache and mock fallback.

Research: research.md #11 for full endpoint list.
Free-tier guard: cache TTL 300s per AGENTS.md #6, retries with backoff, mock JSON when USE_MOCK_IMD=true or IP not whitelisted.

Usage:
    from imd_client import get_city_forecast_7d, get_district_nowcast, ...
    data = await get_city_forecast_7d(district_id="528")
"""
import json
import os
import pathlib
import time
from typing import Any, Dict, Optional

import httpx
from cachetools import TTLCache
from tenacity import retry, stop_after_attempt, wait_exponential

# Base IMD gateway — whitelisting required at https://api.imd.gov.in/public/index.php
IMD_BASE = os.getenv("IMD_API_URL", "https://api.imd.gov.in/api/v1")
CACHE_TTL = int(os.getenv("CACHE_TTL_SECONDS", "300"))
USE_MOCK = os.getenv("USE_MOCK_IMD", "true").lower() in ("1", "true", "yes")

# In-memory TTL cache (128 entries, 5 min) — no Redis needed for hackathon
cache: TTLCache = TTLCache(maxsize=128, ttl=CACHE_TTL)

# Shared httpx client (reused across calls)
_client: Optional[httpx.AsyncClient] = None

def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=5.0, headers={"Accept": "application/json"})
    return _client

def _cache_key(url: str, params: Optional[Dict[str, Any]] = None) -> str:
    if params:
        return f"{url}?{json.dumps(params, sort_keys=True)}"
    return url

def _mock_path(name: str) -> pathlib.Path:
    # data/sample_imd_responses/ relative to repo root
    # server/src -> ../.. -> repo root
    root = pathlib.Path(__file__).parents[2]
    return root / "data" / "sample_imd_responses" / f"{name}.json"

def _load_mock(name: str) -> Dict[str, Any]:
    p = _mock_path(name)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    # fallback generic mock
    return {
        "status": "success",
        "message": f"Mock {name} — no sample file",
        "source": f"mock:{name}",
        "cached_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "data": [],
    }

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=2))
async def _fetch(url: str, params: Optional[Dict[str, Any]] = None, mock_name: Optional[str] = None) -> Dict[str, Any]:
    """Fetch with cache, retry, and mock fallback."""
    key = _cache_key(url, params)
    if key in cache:
        return cache[key]

    if USE_MOCK and mock_name:
        # In mock mode, return sample JSON immediately (and cache it)
        data = _load_mock(mock_name)
        cache[key] = data
        return data

    # Live fetch
    try:
        client = _get_client()
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        # Ensure attribution fields
        if "source" not in data:
            data["source"] = url
        if "cached_at" not in data:
            data["cached_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        cache[key] = data
        return data
    except Exception as e:
        # On failure, try mock fallback instead of bubbling 500 to voice agent
        if mock_name:
            data = _load_mock(mock_name)
            # annotate that it is fallback due to error
            data["_fallback_reason"] = str(e)
            cache[key] = data
            return data
        raise

# --- Tool wrappers (one per IMD endpoint group) ---

async def get_city_forecast_7d(district_id: str) -> Dict[str, Any]:
    """City Weather Forecast (7 Days) — GET /api/v1/cityforecast?id={district_id}"""
    url = f"{IMD_BASE}/cityforecast"
    return await _fetch(url, params={"id": district_id}, mock_name="cityforecast_pune")

async def get_city_forecast_latlon(lat: float, lon: float) -> Dict[str, Any]:
    """City with Lat/Lon — GET /api/v1/cityforecast?lat=&lon="""
    url = f"{IMD_BASE}/cityforecast"
    return await _fetch(url, params={"lat": lat, "lon": lon}, mock_name="cityforecast_pune")

async def get_district_nowcast(district_id: str) -> Dict[str, Any]:
    """District-wise Nowcast — GET /api/v1/districtnowcast?id={district_id}"""
    url = f"{IMD_BASE}/districtnowcast"
    return await _fetch(url, params={"id": district_id}, mock_name="districtnowcast_pune")

async def get_station_nowcast(station_id: str) -> Dict[str, Any]:
    """Station-wise Nowcast — GET /api/v1/stationnowcast?id={station_id}"""
    url = f"{IMD_BASE}/stationnowcast"
    return await _fetch(url, params={"id": station_id}, mock_name="districtnowcast_pune")

async def get_rainfall_stats(district_id: Optional[str] = None, state: Optional[str] = None) -> Dict[str, Any]:
    """District-wise Rainfall + Subdivision forecast — mock combines both."""
    url = f"{IMD_BASE}/districtrainfall"
    params = {}
    if district_id:
        params["id"] = district_id
    # mock reuse
    return await _fetch(url, params=params or None, mock_name="cityforecast_pune")

async def get_fishermen_warning(district_id: Optional[str] = None) -> Dict[str, Any]:
    """Fishermen Warning — GET /api/v1/fishermenwarning"""
    url = f"{IMD_BASE}/fishermenwarning"
    params = {"id": district_id} if district_id else None
    # choose mock based on coastal district
    mock = "fishermen_warning_nagapattinam"
    return await _fetch(url, params=params, mock_name=mock)

async def get_sea_area_bulletin() -> Dict[str, Any]:
    """Sea Area Bulletin + Coastal + Port — GET /api/v1/seaareabulletin"""
    url = f"{IMD_BASE}/seaareabulletin"
    return await _fetch(url, mock_name="fishermen_warning_nagapattinam")

async def get_coastal_bulletin() -> Dict[str, Any]:
    """Coastal Bulletin — GET /api/v1/coastalbulletin"""
    url = f"{IMD_BASE}/coastalbulletin"
    return await _fetch(url, mock_name="fishermen_warning_nagapattinam")

async def get_port_warning() -> Dict[str, Any]:
    """Port Warning — GET /api/v1/portwarning"""
    url = f"{IMD_BASE}/portwarning"
    return await _fetch(url, mock_name="fishermen_warning_nagapattinam")

async def get_cyclone_track() -> Dict[str, Any]:
    """Cyclone Track — GET /api/v1/cyclonetrack"""
    url = f"{IMD_BASE}/cyclonetrack"
    return await _fetch(url, mock_name="cyclonetrack_mock")

async def get_cyclone_wind() -> Dict[str, Any]:
    """Cyclone Wind Warning GeoJSON — GET /api/v1/cyclonewind"""
    url = f"{IMD_BASE}/cyclonewind"
    return await _fetch(url, mock_name="cyclonetrack_mock")

async def get_cyclone_cou() -> Dict[str, Any]:
    """Cone of Uncertainty — GET /api/v1/cyclonecou"""
    url = f"{IMD_BASE}/cyclonecou"
    return await _fetch(url, mock_name="cyclonetrack_mock")

async def get_all_india_warning(district_id: Optional[str] = None) -> Dict[str, Any]:
    """District/Subdivision Warnings — GET /api/v1/districtwarning"""
    url = f"{IMD_BASE}/districtwarning"
    params = {"id": district_id} if district_id else None
    return await _fetch(url, params=params, mock_name="districtnowcast_pune")

async def get_agromet_advisory(district_id: str) -> Dict[str, Any]:
    """Agromet bulletin — reuses forecast mock (real agromet API not public, mock for hackathon)."""
    url = f"{IMD_BASE}/agromet"
    return await _fetch(url, params={"id": district_id}, mock_name="cityforecast_pune")

async def get_sun_moon(lat: float, lon: float) -> Dict[str, Any]:
    """Sun Moon Rise/Set — GET /api/v1/sunmoon?lat=&lon="""
    url = f"{IMD_BASE}/sunmoon"
    return await _fetch(url, params={"lat": lat, "lon": lon}, mock_name="cityforecast_pune")

# Utility for tests / health
def clear_cache() -> None:
    cache.clear()

def cache_info() -> Dict[str, Any]:
    return {"size": len(cache), "maxsize": cache.maxsize, "ttl": cache.ttl, "use_mock": USE_MOCK}
