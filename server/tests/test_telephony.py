"""Tests for Phase 6.3 telephony (plan.md 6.3).

POST /dial + /hangup wrap the Agora Telephony Beta (SIP). Without the Beta
grant they answer 501 with setup steps; the phone-bridge fallback covers demos.
No Agora cloud needed — FakeAgent stands in for the SDK.
"""


def test_dial_rejects_bad_number(client):
    response = client.post("/dial", json={"toNumber": "not-a-number"})
    assert response.status_code == 400
    assert "E.164" in response.json()["detail"]


def test_dial_rejects_missing_country_code(client):
    response = client.post("/dial", json={"toNumber": "9876543210"})
    assert response.status_code == 400


def test_dial_without_beta_returns_501_guide(client):
    response = client.post("/dial", json={"toNumber": "+919876543210"})
    assert response.status_code == 501
    assert "Telephony Beta" in response.json()["detail"]
    assert client.fake_agent.dial_calls == []


def test_dial_enabled_paths_shape(client):
    client.fake_agent.telephony_enabled = True
    response = client.post(
        "/dial",
        json={"toNumber": "+91 98765 43210", "language": "hi-IN", "persona": "farmer"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["agent_id"] == "fake-tel-1"
    assert data["to_number"] == "+919876543210"
    assert data["status"] == "calling"
    assert client.fake_agent.dial_calls == [("+919876543210", None, "hi-IN", "farmer")]


def test_hangup_without_beta_returns_501(client):
    assert client.post("/hangup", json={"agentId": "fake-tel-1"}).status_code == 501


def test_hangup_enabled_calls_agent(client):
    client.fake_agent.telephony_enabled = True
    response = client.post("/hangup", json={"agentId": "fake-tel-1"})
    assert response.status_code == 200
    assert response.json()["code"] == 0
    assert client.fake_agent.hangup_calls == ["fake-tel-1"]


def test_hangup_unknown_agent_maps_to_400(client):
    client.fake_agent.telephony_enabled = True
    assert client.post("/hangup", json={"agentId": "unknown-id"}).status_code == 400


def test_telephony_status_reports_mode(client):
    # Route is env-based (works even with the FakeAgent): default env has no
    # Beta grant, so the phone-bridge fallback is advertised.
    response = client.get("/telephonyStatus")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["enabled"] is False
    assert data["mode"] == "phone-bridge-fallback"


def test_telephony_webhook_accepts_any_event(client):
    for payload in (
        {"event": 201, "call_state": "ringing"},
        {"event": 202, "call_state": "answered"},
        {"anything": "goes"},
    ):
        response = client.post("/telephonyWebhook", json=payload)
        assert response.status_code == 200
        assert response.json()["code"] == 0


def test_e164_parsing_unit(server_module):
    import agent as agent_module

    assert agent_module.parse_e164_number("+919876543210") == "+919876543210"
    assert agent_module.parse_e164_number("+91 98765 43210") == "+919876543210"
    assert agent_module.parse_e164_number("+1 (415) 555-0100") == "+14155550100"
    for bad in ("", "abc", "+123", "+012345678", "++919876543210"):
        try:
            agent_module.parse_e164_number(bad)
        except ValueError:
            continue
        raise AssertionError(f"should reject {bad!r}")
