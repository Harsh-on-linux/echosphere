# WeatherGPT MCP Server — Phase 3.2 stub
# FastMCP server exposing IMD tools at /mcp for Agora LLM via llm.mcp_servers
# See research.md #6 and plan.md 3.2

"""
Placeholder. Real MCP in Phase 3.2:
from fastmcp import FastMCP
mcp = FastMCP("imd-mcp")

@mcp.tool()
async def resolve_location(location_text: str) -> dict: ...
@mcp.tool()
async def get_city_forecast_7d(district_id: str) -> dict: ...
# + 8 more tools

app.mount("/mcp", mcp.sse_app())
"""

# Keep importable
try:
    from fastmcp import FastMCP  # noqa: F401
    mcp = FastMCP("imd-mcp")
except Exception:
    mcp = None
