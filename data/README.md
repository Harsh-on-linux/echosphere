# VaayuMitra Data

This directory implements **Phase 1.1** folder layout per `plan.md`.

```
data/
├── imd_districts.json       # district_id -> name/state/coastal + aliases for fuzzy resolver
├── imd_stations.json        # AWS/ARG station mapping
└── sample_imd_responses/    # Cached JSON for offline dev (USE_MOCK_IMD=true)
    ├── cityforecast_pune.json
    ├── districtnowcast_pune.json
    ├── fishermen_warning_nagapattinam.json
    └── cyclonetrack_mock.json
```

## Mapping to starter layout

| plan.md | actual scaffold |
|---------|-----------------|
| `frontend/` | `web/` (Next.js 16) |
| `backend/`  | `server/` (FastAPI) |
| `backend/*.py` | `server/src/*.py` |

`server/src/` already contains `server.py` + `agent.py` from quickstart. Upcoming Phase 1.2 adds:
- `server/src/imd_client.py` — IMD wrappers + 300s TTL cache
- `server/src/location_resolver.py` — rapidfuzz resolver over `imd_districts.json`
- `server/src/persona_prompt.py` — farmer/fisherman/disaster prompts
- `server/src/mcp_server.py` — FastMCP tools at `/mcp`

All IMD responses use 5-min cache (`CACHE_TTL_SECONDS=300`) and include `source + cached_at` for attribution.
