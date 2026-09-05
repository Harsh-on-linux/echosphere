# -*- coding: utf-8 -*-
"""
Tests for Phase 5: Caller Memory & Profile Store
Verifies user profile persistence, crop updates, prompt context generation,
FastMCP tool invocations, and FastAPI endpoints.
"""
import json
import pytest

from user_store import (
    add_farmer_crop,
    clear_user_db,
    get_or_create_user,
    get_profile_context,
)


def _sse_json(text: str) -> dict:
    """Extract the JSON-RPC payload from a stateless SSE response body."""
    for line in text.splitlines():
        if line.startswith("data: "):
            return json.loads(line[len("data: "):])
    raise AssertionError(f"no SSE data payload in: {text[:500]}")


@pytest.fixture(autouse=True)
def clean_db():
    clear_user_db()
    yield
    clear_user_db()


def test_get_or_create_user_defaults():
    u = get_or_create_user("+91 98765 43210", name="Ramesh", persona="farmer")
    assert u["phone_number"] == "+919876543210"
    assert u["name"] == "Ramesh"
    assert u["persona"] == "farmer"
    assert u["preferred_language"] == "hi-IN"
    assert u["district"] == "Pune"
    assert "farmer_details" in u


def test_add_and_update_farmer_crop():
    u = get_or_create_user("+919988776655", persona="farmer")
    assert len(u["farmer_details"]["crops"]) == 0

    add_farmer_crop("+919988776655", crop_name="cotton", growth_stage="sowing")
    u2 = get_or_create_user("+919988776655")
    assert len(u2["farmer_details"]["crops"]) == 1
    assert u2["farmer_details"]["crops"][0]["crop"] == "Cotton"
    assert u2["farmer_details"]["crops"][0]["stage"] == "sowing"

    # Update stage of existing crop
    add_farmer_crop("+919988776655", crop_name="cotton", growth_stage="flowering")
    u3 = get_or_create_user("+919988776655")
    assert len(u3["farmer_details"]["crops"]) == 1
    assert u3["farmer_details"]["crops"][0]["stage"] == "flowering"


def test_get_profile_context():
    # Unknown phone
    assert get_profile_context("+910000000000") is None

    # Farmer
    get_or_create_user("+919876543210", name="Suresh", persona="farmer", district="Nagpur", tehsil="Katol")
    add_farmer_crop("+919876543210", "Orange", "fruiting")
    ctx = get_profile_context("+919876543210")
    assert ctx is not None
    assert "Returning Farmer Profile" in ctx
    assert "Suresh" in ctx
    assert "Katol, Nagpur" in ctx
    assert "Orange (fruiting)" in ctx

    # Fisherman
    get_or_create_user("+919123456789", name="Murugan", persona="fisherman")
    ctx_fish = get_profile_context("+919123456789")
    assert ctx_fish is not None
    assert "Returning Fisherman Profile" in ctx_fish
    assert "Murugan" in ctx_fish
    assert "Pamban" in ctx_fish


def test_user_profile_api_endpoints(client):
    with client as c:
        # 1. Create/update profile via POST
        res = c.post(
            "/api/userProfile",
            json={
                "phoneNumber": "+919876543210",
                "name": "Devendra",
                "persona": "farmer",
                "preferredLanguage": "mr-IN",
                "district": "Nashik",
                "tehsil": "Niphad",
            },
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["name"] == "Devendra"
        assert data["preferred_language"] == "mr-IN"
        assert data["district"] == "Nashik"

        # 2. Add crop via POST
        res_crop = c.post(
            "/api/userProfile/crop",
            json={
                "phoneNumber": "+919876543210",
                "cropName": "Grapes",
                "growthStage": "pruning",
            },
        )
        assert res_crop.status_code == 200
        crops = res_crop.json()["data"]["farmer_details"]["crops"]
        assert any(c_item["crop"] == "Grapes" and c_item["stage"] == "pruning" for c_item in crops)

        # 3. GET profile
        res_get = c.get("/api/userProfile?phoneNumber=%2B919876543210")
        assert res_get.status_code == 200
        body = res_get.json()["data"]
        assert body["user"]["name"] == "Devendra"
        assert "Returning Farmer Profile" in body["context"]
        assert "Grapes (pruning)" in body["context"]


def test_start_agent_with_caller_phone(client):
    with client as c:
        get_or_create_user("+919876543210", name="Devendra", persona="farmer", district="Nashik")

        res = c.post(
            "/startAgent",
            json={
                "channelName": "wx-test-caller",
                "rtcUid": 100,
                "userUid": 200,
                "phoneNumber": "+919876543210",
            },
        )
        assert res.status_code == 200
        assert res.json()["data"]["status"] == "started"


def test_mcp_user_store_tools(client):
    get_or_create_user("+919876543210", name="Kisan", persona="farmer")

    # Call get_caller_farm_profile via FastMCP HTTP endpoint
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "get_caller_farm_profile",
            "arguments": {"phone_number": "+919876543210"},
        },
    }
    with client as c:
        resp = c.post(
            "/mcp",
            json=payload,
            headers={"Accept": "application/json, text/event-stream"},
        )
        assert resp.status_code == 200
        data = _sse_json(resp.text)
        assert data["result"]["isError"] is False
        assert "Kisan" in resp.text
