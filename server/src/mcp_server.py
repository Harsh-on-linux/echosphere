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

    @mcp.tool()
    async def get_crop_weather_advisory(
        crop: str,
        location: str,
        rainfall_mm: float = 0.0,
        humidity_percent: float = 65.0,
        temp_max: float = 30.0,
        temp_min: float = 20.0,
        wind_kmh: float = 12.0,
        growth_stage: Optional[str] = None,
    ) -> dict:
        """ICAR-KVK Crop Agro-Advisory: Actionable guidance on pesticide spraying, drainage, and disease risks."""
        from agro_advisory import evaluate_agro_advisory as _fn

        return await _fn(
            crop=crop,
            district_or_location=location,
            rainfall_mm=rainfall_mm,
            humidity_percent=humidity_percent,
            temp_max=temp_max,
            temp_min=temp_min,
            wind_kmh=wind_kmh,
            growth_stage=growth_stage,
        )

    @mcp.tool()
    async def trigger_sos_distress(
        location: str,
        situation: str,
        caller_id: str = "VoiceUser",
        lat: Optional[float] = None,
        lon: Optional[float] = None,
    ) -> dict:
        """Trigger emergency maritime/disaster SOS distress protocol with Coast Guard MRCC routing."""
        from emergency_handler import dispatch_sos_alert as _fn

        return await _fn(
            caller_identifier=caller_id,
            location_text=location,
            situation_summary=situation,
            lat=lat,
            lon=lon,
        )

    @mcp.tool()
    async def get_caller_farm_profile(phone_number: str) -> dict:
        """Lookup returning farmer/fisherman profile by caller phone number."""
        from user_store import get_or_create_user as _fn

        return _fn(phone_number)

    @mcp.tool()
    async def update_crop_record(phone_number: str, crop_name: str, stage: str = "vegetative") -> dict:
        """Record or update an active crop for a farmer's profile."""
        from user_store import add_farmer_crop as _fn

        return _fn(phone_number, crop_name=crop_name, growth_stage=stage)

    @mcp.tool()
    async def get_regional_weather_bulletin(district_name: str, language: str = "hi-IN", persona: str = "farmer") -> dict:
        """Retrieve pre-synthesized 30-second localized weather audio bulletin script and cached audio URL."""
        from bulletin_cache import get_or_create_cached_bulletin as _fn

        return _fn(district_name=district_name, language=language, persona=persona)

except Exception as e:
    # Graceful fallback for dev without fastmcp installed; keep importable for tests
    mcp = None
    _mcp_error = str(e)

def get_mcp():
    return mcp
