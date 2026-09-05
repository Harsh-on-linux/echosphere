# -*- coding: utf-8 -*-
"""
WeatherGPT MCP Server — Phase 1.2 skeleton + Phase 3.2 full tools
Exposes IMD tools via FastMCP at /mcp for Agora Conversational AI Engine (llm.mcp_servers).

See research.md #6 (MCP) and plan.md 3.2:
  mcp = FastMCP("imd-mcp")
  @mcp.tool() async def resolve_location(...) -> dict
  Mount at /mcp for Agora to call via SSE.
"""

from typing import Optional

try:
    from fastmcp import FastMCP

    mcp = FastMCP("imd-mcp")

    @mcp.tool()
    async def resolve_location(location_text: str) -> dict:
        """Resolve spoken place to IMD district_id. Use before any weather tool."""
        from location_resolver import fuzzy_match

        return fuzzy_match(location_text)

    @mcp.tool()
    async def get_city_forecast_7d(district_id: str) -> dict:
        """7-day city forecast — GET /api/v1/cityforecast?id={district_id}"""
        from imd_client import get_city_forecast_7d as _fn

        return await _fn(district_id)

    @mcp.tool()
    async def get_city_forecast_latlon(lat: float, lon: float) -> dict:
        """City forecast by lat/lon — GET /api/v1/cityforecast?lat=&lon="""
        from imd_client import get_city_forecast_latlon as _fn

        return await _fn(lat, lon)

    @mcp.tool()
    async def get_district_nowcast(district_id: str) -> dict:
        """District nowcast — GET /api/v1/districtnowcast?id={district_id}"""
        from imd_client import get_district_nowcast as _fn

        return await _fn(district_id)

    @mcp.tool()
    async def get_rainfall_stats(district_id: str) -> dict:
        """Rainfall stats + subdivision forecast — GET /api/v1/districtrainfall"""
        from imd_client import get_rainfall_stats as _fn

        return await _fn(district_id)

    @mcp.tool()
    async def get_fishermen_warning(district_id: str) -> dict:
        """Fishermen warning — GET /api/v1/fishermenwarning"""
        from imd_client import get_fishermen_warning as _fn

        return await _fn(district_id)

    @mcp.tool()
    async def get_sea_area_bulletin() -> dict:
        """Sea area bulletin (+ coastal + port) — GET /api/v1/seaareabulletin"""
        from imd_client import get_sea_area_bulletin as _fn

        return await _fn()

    @mcp.tool()
    async def get_cyclone_track() -> dict:
        """Cyclone track + wind + cone — GET /api/v1/cyclonetrack"""
        from imd_client import get_cyclone_track as _fn

        return await _fn()

    @mcp.tool()
    async def get_agromet_advisory(district_id: str) -> dict:
        """Agromet advisory — bulletins for farmers"""
        from imd_client import get_agromet_advisory as _fn

        return await _fn(district_id)

    @mcp.tool()
    async def get_all_india_warning(district_id: Optional[str] = None) -> dict:
        """All-India district/subdivision warnings"""
        from imd_client import get_all_india_warning as _fn

        return await _fn(district_id)

    @mcp.tool()
    async def get_subdivision_warning(subdivision: Optional[str] = None) -> dict:
        """Subdivision warnings for state-wide queries — GET /api/v1/subdivisionwarning"""
        from imd_client import get_subdivision_warning as _fn

        return await _fn(subdivision)

    @mcp.tool()
    async def resolve_with_fallback(location_text: str) -> dict:
        """Resolve + spatial fallback: candidates + nearest lat/lon + state_hint. Use when resolve_location confidence is low."""
        from location_resolver import resolve_with_fallback as _fn

        return _fn(location_text)

    @mcp.tool()
    async def get_forecast_for_location(location_text: str) -> dict:
        """One-call forecast: resolve -> district forecast, else lat/lon retry. Returns clarification payload for unknown places."""
        from imd_client import get_forecast_for_location as _fn

        return await _fn(location_text)

    @mcp.tool()
    async def get_openmeteo_forecast(lat: float, lon: float) -> dict:
        """Live 7-day secondary forecast (ECMWF/GFS) via Open-Meteo by coordinates. Zero-downtime failover."""
        from openmeteo_client import get_openmeteo_forecast as _fn

        return await _fn(lat, lon)

    @mcp.tool()
    async def get_ocean_state_forecast(coastal_district: str) -> dict:
        """INCOIS Ocean State Forecast: wave height, swell period, currents, and vessel safety."""
        from incois_client import get_ocean_state_forecast as _fn

        return await _fn(coastal_district)

    @mcp.tool()
    async def get_high_wave_alert(coastal_district: str) -> dict:
        """INCOIS High Wave & Swell Surge warning for coastal fishermen safety."""
        from incois_client import get_high_wave_alert as _fn

        return await _fn(coastal_district)

    @mcp.tool()
    async def get_potential_fishing_zone(coastal_district: str) -> dict:
        """INCOIS Potential Fishing Zone (PFZ): satellite-derived fish shoal coordinates and bearing."""
        from incois_client import get_potential_fishing_zone as _fn

        return await _fn(coastal_district)

except Exception as e:
    # Graceful fallback for dev without fastmcp installed; keep importable for tests
    mcp = None
    _mcp_error = str(e)

def get_mcp():
    return mcp
