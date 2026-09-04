# -*- coding: utf-8 -*-
"""
Agora Agent & Token Service

HTTP APIs:
- GET  /get_config     -> Agent.generate_config()
- POST /startAgent     -> Agent.start()
- POST /stopAgent      -> Agent.stop()
"""
import logging
import os
import random
import time
from typing import Any, Dict, Optional
from dotenv import load_dotenv

# The Agora CLI writes the Python quickstart environment to server/.env.
_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_base_dir, '.env'), override=True)

from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agora_agent.agentkit.token import generate_convo_ai_token
from agent import Agent

# WeatherGPT additions (Phase 1.2)
try:
    import imd_client  # noqa: F401
    import location_resolver  # noqa: F401
except Exception:
    imd_client = None
    location_resolver = None

# Phase 3.2/3.3 — FastMCP IMD tools at POST /mcp (Agora llm.mcp_servers).
# Mount the streamable-HTTP app (matches SDK default transport) at root with
# path="/mcp" so the final route is exactly /mcp (not /mcp/mcp).
# stateless_http=True: each JSON-RPC POST is self-contained (no session
# handshake), which suits Agora tool calls + TestClient verification.
logger = logging.getLogger("uvicorn.error")

_mcp_http_app = None
try:
    from mcp_server import get_mcp

    _mcp = get_mcp()
    if _mcp is not None:
        _mcp_http_app = _mcp.http_app(path="/mcp", stateless_http=True)
except Exception as e:
    logger.warning("MCP server unavailable: %s", e)
    _mcp_http_app = None


def _log_route_error(route: str, exc: Exception, **context) -> None:
    """Log route failures with safe request context and a traceback."""
    safe_context = {key: value for key, value in context.items() if value is not None}
    logger.exception(
        "Request failed route=%s context=%s error_type=%s error=%s",
        route,
        safe_context,
        type(exc).__name__,
        exc,
    )


def _to_http_error(exc: Exception) -> HTTPException:
    """Convert SDK exceptions to HTTP errors"""
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, RuntimeError):
        return HTTPException(status_code=500, detail=str(exc))
    return HTTPException(status_code=500, detail=f"Internal error: {exc}")


def _serialize(payload: Any) -> Any:
    """Convert SDK pydantic responses to JSON-safe structures."""
    if payload is None:
        return None
    if hasattr(payload, "model_dump"):
        return payload.model_dump(mode="json")
    if hasattr(payload, "dict"):
        return payload.dict()
    if isinstance(payload, (str, int, float, bool)):
        return payload
    if isinstance(payload, dict):
        return {key: _serialize(value) for key, value in payload.items()}
    if isinstance(payload, (list, tuple)):
        return [_serialize(item) for item in payload]
    return str(payload)

try:
    agent = Agent()
except ValueError as e:
    logger.exception(
        "Failed to initialize Agora Agent SDK. Service will fail if endpoints are called without proper configuration: %s",
        e,
    )
    agent = None


def _cors_origins() -> list:
    """Allowed browser origins (plan.md 6.1 deploy).

    Local dev (Next on :3000 -> FastAPI on :8000) works out of the box.
    In prod, set FRONTEND_URL to the Vercel URL (comma-separated ok for
    preview deployments). Explicit list — never "*" with credentials.
    """
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    raw = (os.getenv("FRONTEND_URL") or "").strip()
    for part in raw.split(","):
        origin = part.strip().rstrip("/")
        if origin and origin not in origins:
            origins.append(origin)
    return origins


def _deploy_urls() -> dict:
    """Public URLs Agora + browser need in prod (plan.md 6.1).

    Agora requires HTTPS for llm.mcp_servers, so /health reports whether
    the configured MCP URL satisfies that before any voice session starts.
    """
    backend_url = (os.getenv("BACKEND_URL") or "").strip().rstrip("/")
    mcp_url = (os.getenv("MCP_SERVER_URL") or "").strip()
    if not mcp_url and backend_url:
        mcp_url = f"{backend_url}/mcp"
    return {
        "backend_url": backend_url or None,
        "mcp_url": mcp_url or None,
        "mcp_public_https": mcp_url.startswith("https://"),
        "frontend_url_configured": bool((os.getenv("FRONTEND_URL") or "").strip()),
    }


# FastAPI application
# Phase 3.2: forward the MCP lifespan so POST /mcp works when mounted
# (FastMCP ASGI integration requires lifespan=mcp_app.lifespan).
_mcp_lifespan = _mcp_http_app.lifespan if _mcp_http_app is not None else None
app = FastAPI(
    title="Agora Agent & Token Service",
    version="2.0.0",
    description="Agora Conversational AI service",
    lifespan=_mcp_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _cyclone_geojson(track_payload: Any) -> Dict[str, Any]:
    """Convert an IMD cyclonetrack payload to a GeoJSON FeatureCollection.

    Emits one Point (current position) + one LineString (forecast track) +
    one Polygon/MultiPolygon (cone of uncertainty) per cyclone entry, all in
    [lon, lat] order. Unknown shapes pass through untouched; missing pieces
    are skipped so the map never breaks on a partial IMD response.
    """
    features: list = []
    entries = []
    if isinstance(track_payload, dict):
        data = track_payload.get("data")
        entries = data if isinstance(data, list) else []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = entry.get("cyclone_name")
        pos = entry.get("current_position") or {}
        try:
            lat, lon = float(pos["lat"]), float(pos["lon"])
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "kind": "position", "name": name,
                    "category": pos.get("category"), "msw_kts": pos.get("msw_kts"),
                },
            })
        except (KeyError, TypeError, ValueError):
            pass
        line: list = []
        for fix in entry.get("forecast_track") or []:
            try:
                line.append([float(fix["lon"]), float(fix["lat"])])
            except (KeyError, TypeError, ValueError):
                continue
        if len(line) >= 2:
            features.append({
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": line},
                "properties": {"kind": "track", "name": name},
            })
        cone = entry.get("cone_of_uncertainty") or {}
        if cone.get("type") in ("Polygon", "MultiPolygon") and cone.get("coordinates"):
            features.append({
                "type": "Feature",
                "geometry": {"type": cone["type"], "coordinates": cone["coordinates"]},
                "properties": {"kind": "cone", "name": name},
            })
    meta = track_payload if isinstance(track_payload, dict) else {}
    return {
        "type": "FeatureCollection",
        "features": features,
        "cyclone_name": next(
            (e.get("cyclone_name") for e in entries if isinstance(e, dict) and e.get("cyclone_name")),
            None,
        ),
        "source": meta.get("source", "IMD api.imd.gov.in/api/v1/cyclonetrack"),
        "cached_at": meta.get("cached_at"),
    }


router = APIRouter()


# Request models
class StartAgentRequest(BaseModel):
    """Request body for POST /startAgent"""
    channelName: str
    rtcUid: int
    userUid: int
    parameters: Optional[Dict[str, Any]] = None
    language: Optional[str] = None
    persona: Optional[str] = None


class StopAgentRequest(BaseModel):
    """Request body for POST /stopAgent"""
    agentId: str


class InterruptAgentRequest(BaseModel):
    """Request body for POST /interruptAgent (plan.md 2.2 manual interrupt)"""
    agentId: str


class TokenRequest(BaseModel):
    """Request body for POST /api/token (plan.md 1.3)"""
    channel: Optional[str] = None
    uid: Optional[int] = None


# --- Health & Token (Phase 1.2/1.3) ---

@router.get("/health")
async def health():
    """Health check for WeatherGPT + Agora readiness"""
    info = {}
    if imd_client is not None:
        try:
            info = imd_client.cache_info()  # type: ignore
        except Exception:
            info = {"cache": "unknown"}
    return {
        "status": "ok",
        "service": "weathergpt",
        "version": "1.2.0",
        "agora_configured": agent is not None,
        "imd_cache": info,
        **_deploy_urls(),
    }


@router.post("/api/token")
async def api_token(request: TokenRequest):
    """POST /api/token {channel, uid} -> {rtcToken, rtmToken} alias for /get_config (plan.md 1.3)"""
    if agent is None:
        raise HTTPException(status_code=500, detail="Service not properly configured.")
    try:
        user_uid = random.randint(1000, 9999999) if request.uid is None or request.uid <= 0 else request.uid
        channel_name = request.channel or _generate_channel_name()
        app_id = os.getenv("AGORA_APP_ID")
        app_certificate = os.getenv("AGORA_APP_CERTIFICATE")
        token = generate_convo_ai_token(
            app_id=app_id,
            app_certificate=app_certificate,
            channel_name=channel_name,
            uid=user_uid,
            token_expire=3600,
        )
        return {"rtcToken": token, "rtmToken": token, "channel": channel_name, "uid": str(user_uid), "app_id": app_id}
    except Exception as e:
        _log_route_error("/api/token", e, channel=request.channel, uid=request.uid)
        raise _to_http_error(e)


# API endpoints
def _generate_channel_name() -> str:
    return f"ai-conversation-{int(time.time())}-{random.randint(1000, 9999)}"


@router.get("/get_config")
async def get_config(
    channel: Optional[str] = Query(default=None),
    uid: Optional[int] = Query(default=None),
):
    """Generate connection configuration"""
    if agent is None:
        raise HTTPException(
            status_code=500,
            detail="Service not properly configured. Please check environment variables.",
        )

    try:
        # Agora RTC accepts uid=0 as "auto assign", but RTM token subjects cannot
        # use 0. Replace missing, zero, or negative values with a generated UID.
        user_uid = random.randint(1000, 9999999) if uid is None or uid <= 0 else uid
        agent_uid = str(random.randint(10000000, 99999999))
        channel_name = channel or _generate_channel_name()

        # Get credentials from environment
        app_id = os.getenv("AGORA_APP_ID")
        app_certificate = os.getenv("AGORA_APP_CERTIFICATE")

        # Generate a one-hour RTC+RTM token and renew it client-side as needed.
        token = generate_convo_ai_token(
            app_id=app_id,
            app_certificate=app_certificate,
            channel_name=channel_name,
            uid=user_uid,
            token_expire=3600,
        )

        config_data = {
            "app_id": app_id,
            "token": token,
            "uid": str(user_uid),
            "channel_name": channel_name,
            "agent_uid": agent_uid,
        }

        return {
            "code": 0,
            "data": config_data,
            "msg": "success",
        }
    except Exception as e:
        _log_route_error("/get_config", e, channel=channel, uid=uid)
        raise _to_http_error(e)


@router.post("/startAgent")
async def start_agent(request: StartAgentRequest):
    """Start agent in a channel"""
    if agent is None:
        raise HTTPException(
            status_code=500,
            detail="Service not properly configured. Please check environment variables.",
        )

    try:
        output_audio_codec = None
        if request.parameters:
            output_audio_codec = request.parameters.get("output_audio_codec")

        result = await agent.start(
            channel_name=request.channelName,
            agent_uid=request.rtcUid,
            user_uid=request.userUid,
            output_audio_codec=output_audio_codec,
            language=request.language,
            persona=request.persona,
        )
        return {"code": 0, "msg": "success", "data": result}
    except Exception as e:
        _log_route_error(
            "/startAgent",
            e,
            channelName=request.channelName,
            rtcUid=request.rtcUid,
            userUid=request.userUid,
        )
        raise _to_http_error(e)


@router.post("/stopAgent")
async def stop_agent(request: StopAgentRequest):
    """Stop agent by ID"""
    if agent is None:
        raise HTTPException(
            status_code=500,
            detail="Service not properly configured. Please check environment variables.",
        )

    try:
        await agent.stop(request.agentId)
        return {"code": 0, "msg": "success"}
    except Exception as e:
        _log_route_error("/stopAgent", e, agentId=request.agentId)
        raise _to_http_error(e)


# --- Leave & conversation control (Phase 2.3) ---
# idle_timeout=120 on every session auto-leaves after 2 min silence so no
# free-tier minutes burn when a tab closes without an explicit leave.

@router.post("/interruptAgent")
async def interrupt_agent(request: InterruptAgentRequest):
    """Manually interrupt a speaking/thinking agent (plan.md 2.2/5.1 demo)"""
    if agent is None:
        raise HTTPException(
            status_code=500,
            detail="Service not properly configured. Please check environment variables.",
        )

    try:
        await agent.interrupt(request.agentId)
        return {"code": 0, "msg": "success"}
    except Exception as e:
        _log_route_error("/interruptAgent", e, agentId=request.agentId)
        raise _to_http_error(e)


@router.get("/agentHistory")
async def agent_history(agentId: str = Query(default=...)):
    """Conversation history for verification (plan.md 2.1: check turns/latency)"""
    if agent is None:
        raise HTTPException(
            status_code=500,
            detail="Service not properly configured. Please check environment variables.",
        )

    try:
        history = await agent.get_history(agentId)
        return {"code": 0, "msg": "success", "data": _serialize(history)}
    except Exception as e:
        _log_route_error("/agentHistory", e, agentId=agentId)
        raise _to_http_error(e)


@router.get("/agentTurns")
async def agent_turns(
    agentId: str = Query(default=...),
    pageIndex: Optional[int] = Query(default=None),
    pageSize: Optional[int] = Query(default=None),
):
    """Per-turn latency metrics (plan.md 2.1: target <1s ASR+LLM+TTS)"""
    if agent is None:
        raise HTTPException(
            status_code=500,
            detail="Service not properly configured. Please check environment variables.",
        )

    try:
        turns = await agent.get_turns(agentId, page_index=pageIndex, page_size=pageSize)
        return {"code": 0, "msg": "success", "data": _serialize(turns)}
    except Exception as e:
        _log_route_error("/agentTurns", e, agentId=agentId)
        raise _to_http_error(e)


@router.get("/cycloneMap")
async def cyclone_map():
    """Cyclone track + cone as GeoJSON (plan.md 6.2 map sync).

    Built from IMD cyclonetrack (TTL-cached, mock fallback when
    USE_MOCK_IMD=true). Frontend draws it on Leaflet and highlights the
    cone while the agent is speaking.
    """
    if imd_client is None:
        raise HTTPException(status_code=500, detail="IMD client unavailable.")

    try:
        track = await imd_client.get_cyclone_track()  # type: ignore
        return {"code": 0, "msg": "success", "data": _cyclone_geojson(track)}
    except Exception as e:
        _log_route_error("/cycloneMap", e)
        raise _to_http_error(e)


app.include_router(router)

# Mount AFTER the REST router so /health, /get_config, /startAgent etc. keep
# priority and /mcp is served by FastMCP (plan.md 3.2: `curl .../mcp tools/list`).
if _mcp_http_app is not None:
    app.mount("/", _mcp_http_app)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    # proxy_headers: Render/Railway terminate TLS at the edge and forward
    # X-Forwarded-Proto — needed so generated URLs respect https (plan.md 6.1).
    uvicorn.run(app, host="0.0.0.0", port=port, proxy_headers=True, forwarded_allow_ips="*")
