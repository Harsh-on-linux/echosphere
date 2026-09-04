# -*- coding: utf-8 -*-
"""
WeatherGPT Open-Meteo Client — Secondary Meteorological Fallback
Provides live weather forecasting via Open-Meteo (ECMWF / GFS) when IMD gateway
experiences downtime, rate limits, or IP whitelisting delays.

Zero API key required; compliant with open meteorological data standards.
"""
import time
from typing import Any, Dict, Optional

import httpx
from cachetools import TTLCache

OPENMETEO_BASE = "https://api.open-meteo.com/v1/forecast"
_cache = TTLCache(maxsize=128, ttl=300)
_client: Optional[httpx.AsyncClient] = None

# WMO Weather interpretation codes (WW)
WMO_CODES: Dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=6.0, headers={"Accept": "application/json"})
    return _client


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


async def get_openmeteo_forecast(lat: float, lon: float) -> Dict[str, Any]:
    """Fetch 7-day daily weather forecast from Open-Meteo by coordinates."""
    cache_key = f"{lat:.4f},{lon:.4f}"
    if cache_key in _cache:
        return _cache[cache_key]

    params = {
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "daily": [
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "precipitation_probability_max",
            "wind_speed_10m_max",
        ],
        "timezone": "auto",
    }

    client = _get_client()
    try:
        resp = await client.get(OPENMETEO_BASE, params=params)
        resp.raise_for_status()
        raw = resp.json()

        daily = raw.get("daily", {})
        dates = daily.get("time", [])
        codes = daily.get("weather_code", [])
        t_max = daily.get("temperature_2m_max", [])
        t_min = daily.get("temperature_2m_min", [])
        precip = daily.get("precipitation_sum", [])
        precip_prob = daily.get("precipitation_probability_max", [])
        wind = daily.get("wind_speed_10m_max", [])

        days = []
        for i in range(len(dates)):
            wcode = codes[i] if i < len(codes) else 0
            days.append({
                "date": dates[i],
                "temp_max": t_max[i] if i < len(t_max) else None,
                "temp_min": t_min[i] if i < len(t_min) else None,
                "rainfall_mm": precip[i] if i < len(precip) else 0.0,
                "precipitation_probability": precip_prob[i] if i < len(precip_prob) else 0,
                "wind_max_kmh": wind[i] if i < len(wind) else None,
                "weather_desc": WMO_CODES.get(wcode, "Unknown"),
            })

        result = {
            "status": "success",
            "source": "Open-Meteo ECMWF/GFS Fallback (api.open-meteo.com)",
            "cached_at": _now(),
            "latitude": lat,
            "longitude": lon,
            "forecast_days": days,
            "message": f"7-day weather forecast for ({lat:.2f}, {lon:.2f})",
        }
        _cache[cache_key] = result
        return result

    except Exception as exc:
        return {
            "status": "fallback_error",
            "source": "Open-Meteo ECMWF/GFS Fallback",
            "cached_at": _now(),
            "error": str(exc),
            "forecast_days": [],
            "message": "Open-Meteo service temporarily unavailable",
        }


def clear_openmeteo_cache() -> None:
    _cache.clear()
