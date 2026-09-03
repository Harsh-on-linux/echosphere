# WeatherGPT IMD Client — Phase 1.2 stub
# Implements 10 IMD endpoint wrappers with 5m TTL cache (AGENTS.md #6)
# See research.md #11 for full endpoint list.
# TODO(Phase 3.1): implement async httpx wrappers + cachetools.TTLCache
"""
Placeholder for IMD client. Real implementation in Phase 3.1.
Uses USE_MOCK_IMD=true + data/sample_imd_responses/ until whitelisting approved.
"""
from cachetools import TTLCache  # noqa: F401
import httpx  # noqa: F401

CACHE_TTL = 300  # seconds per AGENTS.md #6
cache = TTLCache(maxsize=128, ttl=CACHE_TTL)
