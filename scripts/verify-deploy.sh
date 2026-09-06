#!/usr/bin/env bash
# Phase 6.1 verification: probe a deployed (or local) backend.
# Usage: BACKEND_URL=https://vaayumitra-backend.onrender.com bash scripts/verify-deploy.sh
# Checks: /health is ok, Agora configured, /mcp served, MCP URL is public HTTPS
# (required for Agora llm.mcp_servers in prod).
set -euo pipefail

BACKEND_URL="${BACKEND_URL:-${1:-http://localhost:8000}}"
BACKEND_URL="${BACKEND_URL%/}"

echo "Probing $BACKEND_URL/health ..."
health="$(curl -fsS --max-time 15 "$BACKEND_URL/health")"
echo "$health" | python3 -c "
import json, sys
body = json.load(sys.stdin)
assert body.get('status') == 'ok', f\"unexpected health: {body}\"
print('health: ok, service:', body.get('service'))
print('agora_configured:', body.get('agora_configured'))
print('mcp_url:', body.get('mcp_url'))
print('mcp_public_https:', body.get('mcp_public_https'))
print('frontend_url_configured:', body.get('frontend_url_configured'))
if not body.get('agora_configured'):
    print('WARN: Agora credentials not configured on this backend')
if '$BACKEND_URL'.startswith('https://') and not body.get('mcp_public_https'):
    print('WARN: prod backend but MCP URL is not public HTTPS — Agora tool calls will fail')
    sys.exit(1)
"

echo "Probing $BACKEND_URL/mcp (JSON-RPC tools/list) ..."
code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 -X POST "$BACKEND_URL/mcp" \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}')"
echo "POST /mcp -> HTTP $code"
if [[ "$code" != 2* ]]; then
  echo "WARN: /mcp did not return 2xx (expected 200 with tool list)"
  exit 1
fi
echo "Deploy checks passed for $BACKEND_URL"
