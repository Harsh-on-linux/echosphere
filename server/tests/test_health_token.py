"""Tests for Phase 1.3 token server & env wiring (plan.md 1.3)."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

def test_health_returns_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["service"] == "vaayumitra"
    assert "imd_cache" in data
    assert "agora_configured" in data

def test_post_api_token_returns_rtc_rtm(client):
    r = client.post("/api/token", json={"channel": "test-channel", "uid": 12345})
    assert r.status_code == 200
    data = r.json()
    assert "rtcToken" in data
    assert "rtmToken" in data
    assert data["channel"] == "test-channel"
    assert data["uid"] == "12345"
    assert len(data["rtcToken"]) > 20

def test_post_api_token_auto_channel_and_uid(client):
    r = client.post("/api/token", json={})
    assert r.status_code == 200
    data = r.json()
    assert data["channel"].startswith("ai-conversation-")
    assert data["uid"] != "0"
    assert int(data["uid"]) > 0

def test_post_api_token_remaps_zero_uid(client):
    r = client.post("/api/token", json={"channel": "ch", "uid": 0})
    assert r.status_code == 200
    assert r.json()["uid"] != "0"

def test_get_config_still_works_after_health_token(client):
    # Regression: existing get_config must still pass
    r = client.get("/get_config", params={"channel": "regression"})
    assert r.status_code == 200
    assert r.json()["data"]["channel_name"] == "regression"
