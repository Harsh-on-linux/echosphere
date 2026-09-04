"""Phase 3.3: MCP at POST /mcp + llm.mcp_servers wiring (plan.md 3.2/3.3)."""
import asyncio
import json
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))


def _sse_json(text):
    """Extract the JSON-RPC payload from a stateless SSE response body."""
    for line in text.splitlines():
        if line.startswith("data: "):
            return json.loads(line[len("data: "):])
    raise AssertionError(f"no SSE data payload in: {text[:500]}")


def test_mcp_tools_list_exposes_imd_tools(client):
    with client as c:
        r = c.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            headers={"Accept": "application/json, text/event-stream"},
        )
    assert r.status_code == 200
    payload = _sse_json(r.text)
    names = {t["name"] for t in payload["result"]["tools"]}
    for expected in ("resolve_location", "get_city_forecast_7d",
                     "get_district_nowcast", "get_fishermen_warning",
                     "get_cyclone_track", "get_agromet_advisory",
                     "get_all_india_warning"):
        assert expected in names, f"missing MCP tool: {expected}"


def test_mcp_resolve_location_call(client):
    with client as c:
        r = c.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                  "params": {"name": "resolve_location",
                             "arguments": {"location_text": "Bombay"}}},
            headers={"Accept": "application/json, text/event-stream"},
        )
    assert r.status_code == 200
    payload = _sse_json(r.text)
    assert payload["result"]["isError"] is False
    structured = payload["result"]["structuredContent"]
    assert structured["district_id"] == "533"
    assert structured["district_name"] == "Mumbai City"


def _start_and_capture_llm(fake_env, monkeypatch, agent_mod_name="agent"):
    sys.modules.pop(agent_mod_name, None)
    import agent as agent_mod
    captured = {}

    class FakeSession:
        async def start(self):
            return "test-agent-id"

    def fake_create_async_session(self, **kwargs):
        captured["llm"] = self.llm
        captured["config"] = self.config
        return FakeSession()

    from agora_agent.agentkit import Agent as AgoraAgent
    monkeypatch.setattr(AgoraAgent, "create_async_session", fake_create_async_session)
    instance = agent_mod.Agent()
    asyncio.run(instance.start(channel_name="ch", agent_uid=111, user_uid=222))
    return agent_mod, captured


def test_agent_wires_mcp_servers_from_backend_url(fake_env, monkeypatch):
    monkeypatch.setenv("BACKEND_URL", "https://example.com")
    monkeypatch.delenv("MCP_SERVER_URL", raising=False)
    agent_mod, captured = _start_and_capture_llm(fake_env, monkeypatch)
    mcp = captured["llm"].get("mcp_servers")
    assert mcp == [{"url": "https://example.com/mcp",
                    "transport": "streamable_http", "name": "imd"}]
    # enable_tools stays on so Agora actually calls the MCP server
    adv = captured["config"].get("advanced_features")
    enabled = adv.get("enable_tools") if isinstance(adv, dict) else getattr(adv, "enable_tools", None)
    assert enabled is True


def test_agent_prefers_explicit_mcp_server_url(fake_env, monkeypatch):
    monkeypatch.setenv("BACKEND_URL", "https://example.com")
    monkeypatch.setenv("MCP_SERVER_URL", "https://mcp.example.com/imd")
    agent_mod, captured = _start_and_capture_llm(fake_env, monkeypatch)
    assert captured["llm"]["mcp_servers"][0]["url"] == "https://mcp.example.com/imd"


def test_agent_omits_mcp_servers_when_unconfigured(fake_env, monkeypatch):
    monkeypatch.delenv("BACKEND_URL", raising=False)
    monkeypatch.delenv("MCP_SERVER_URL", raising=False)
    agent_mod, captured = _start_and_capture_llm(fake_env, monkeypatch)
    assert captured["llm"].get("mcp_servers") is None
    # Managed OpenAI shape unchanged (Phase 2 regression)
    assert captured["llm"]["url"] == "https://api.openai.com/v1/chat/completions"
