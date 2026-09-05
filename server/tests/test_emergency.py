"""Phase 3 tests: Zero-hallucination safety guardrails & Maritime SOS distress triage."""
import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import pytest
import emergency_handler


def _sse_json(text):
    for line in text.splitlines():
        if line.startswith("data: "):
            return json.loads(line[len("data: "):])
    raise AssertionError(f"no SSE data payload in: {text[:500]}")


@pytest.mark.parametrize("phrase,expected", [
    ("Hamaari naav doob rahi hai, bachao!", True),
    ("Mayday mayday, boat sinking near Rameswaram", True),
    ("Engine failed in rough sea, water entering", True),
    ("Samundar me phans gaye hain toofan me", True),
    ("Pune me kal barish hogi kya?", False),
    ("Is it safe to go fishing tomorrow?", False),
    ("", False),
    (None, False),
])
def test_detect_distress_intent(phrase, expected):
    assert emergency_handler.detect_distress_intent(phrase) == expected


@pytest.mark.asyncio
async def test_dispatch_sos_alert_records_mrcc_event():
    res = await emergency_handler.dispatch_sos_alert(
        caller_identifier="+919876543210",
        location_text="15 km off Nagapattinam",
        situation_summary="Engine stalled, hull breach, high waves",
        lat=10.76,
        lon=79.95,
    )
    assert res["status"] == "SOS_DISPATCHED"
    assert "Coast Guard" in res["spoken_instructions"]
    assert "VHF Channel 16" in res["spoken_instructions"]
    assert res["alert_record"]["caller"] == "+919876543210"
    assert res["alert_record"]["coordinates"] == {"lat": 10.76, "lon": 79.95}


def test_format_deterministic_red_alert():
    bulletin = {
        "cyclone_name": "Cyclone Dana",
        "category": "Very Severe Cyclonic Storm",
        "source": "IMD Special Tropical Weather Outlook",
        "cached_at": "2026-09-05T06:00:00Z"
    }
    rendered = emergency_handler.format_deterministic_red_alert(bulletin)
    assert "OFFICIAL IMD RED WARNING" in rendered
    assert "Cyclone Dana" in rendered
    assert "Very Severe Cyclonic Storm" in rendered
    assert "Total suspension of fishing operations" in rendered


def test_mcp_exposes_sos_distress_tool(client):
    with client as c:
        r = c.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            headers={"Accept": "application/json, text/event-stream"},
        )
    assert r.status_code == 200
    payload = _sse_json(r.text)
    tool_names = {t["name"] for t in payload["result"]["tools"]}
    assert "trigger_sos_distress" in tool_names
