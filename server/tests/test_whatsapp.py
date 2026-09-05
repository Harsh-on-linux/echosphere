"""Phase 4 tests: WhatsApp two-way voice note webhook & Disaster OBD broadcast."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import pytest
import whatsapp_service


def test_whatsapp_verify_webhook_success(client):
    with client as c:
        r = c.get(
            "/api/whatsapp/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "weathergpt_verify_token_2026",
                "hub.challenge": "123456789",
            },
        )
    assert r.status_code == 200
    assert r.text == "123456789"


def test_whatsapp_verify_webhook_forbidden(client):
    with client as c:
        r = c.get(
            "/api/whatsapp/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong_token",
                "hub.challenge": "123456789",
            },
        )
    assert r.status_code == 403


def test_whatsapp_incoming_voice_note(client):
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "id": "wamid.test.123",
                        "from": "919876543210",
                        "type": "audio",
                        "audio": {"id": "media.audio.001"}
                    }]
                }
            }]
        }]
    }
    with client as c:
        r = c.post("/api/whatsapp/webhook", json=payload)
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["status"] == "success"
    assert data["processed_count"] == 1
    event = data["events"][0]
    assert event["from"] == "919876543210"
    assert event["status"] == "voice_note_processed"
    assert "barish" in event["reply_text"].lower() or "imd" in event["reply_text"].lower()


def test_disaster_obd_broadcast_endpoint(client):
    req = {
        "targetNumbers": ["+919876543210", "+919876543211"],
        "bulletinText": "Official IMD Red Alert: Cyclone Dana landfall expected in 6 hours. Stay indoors.",
        "districtName": "Puri",
        "language": "or-IN",
    }
    with client as c:
        r = c.post("/api/disasterBroadcast", json=req)
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["status"] == "success"
    assert data["queued_calls"] == 2
    assert "Puri" in data["message"]
