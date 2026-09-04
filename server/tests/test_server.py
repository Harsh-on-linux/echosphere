"""FastAPI route tests via TestClient + FakeAgent (no Agora cloud)."""


def test_get_config_returns_envelope_and_token(client):
    response = client.get("/get_config")
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["msg"] == "success"
    data = body["data"]
    assert data["app_id"] == "0123456789abcdef0123456789abcdef"
    assert isinstance(data["token"], str) and len(data["token"]) > 0
    assert data["uid"] and data["uid"] != "0"
    assert data["channel_name"].startswith("ai-conversation-")
    assert data["agent_uid"]


def test_get_config_remaps_zero_uid_and_honors_channel(client):
    response = client.get("/get_config", params={"uid": 0, "channel": "test-channel"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["uid"] != "0"
    assert data["channel_name"] == "test-channel"


def test_start_agent_calls_agent_and_returns_shape(client):
    response = client.post(
        "/startAgent",
        json={"channelName": "ch", "rtcUid": 111, "userUid": 222},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"] == {
        "agent_id": "fake-agent-111",
        "channel_name": "ch",
        "status": "started",
    }
    assert client.fake_agent.started == [("ch", 111, 222, None)]


def test_start_agent_forwards_output_audio_codec(client):
    client.post(
        "/startAgent",
        json={
            "channelName": "ch",
            "rtcUid": 111,
            "userUid": 222,
            "parameters": {"output_audio_codec": "opus"},
        },
    )
    assert client.fake_agent.started[-1] == ("ch", 111, 222, "opus")


def test_stop_agent(client):
    response = client.post("/stopAgent", json={"agentId": "fake-agent-111"})
    assert response.status_code == 200
    assert response.json()["code"] == 0
    assert client.fake_agent.stopped == ["fake-agent-111"]


def test_interrupt_agent_calls_agent_and_returns_shape(client):
    response = client.post("/interruptAgent", json={"agentId": "fake-agent-111"})
    assert response.status_code == 200
    assert response.json()["code"] == 0
    assert client.fake_agent.interrupted == ["fake-agent-111"]


def test_interrupt_unknown_agent_maps_to_400(client):
    response = client.post("/interruptAgent", json={"agentId": "unknown-id"})
    assert response.status_code == 400


def test_agent_history_returns_data(client):
    response = client.get("/agentHistory", params={"agentId": "fake-agent-111"})
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"] == {"contents": []}
    assert client.fake_agent.history_calls == ["fake-agent-111"]


def test_agent_history_unknown_agent_maps_to_400(client):
    assert client.get("/agentHistory", params={"agentId": "unknown-id"}).status_code == 400


def test_agent_turns_forwards_pagination(client):
    response = client.get(
        "/agentTurns",
        params={"agentId": "fake-agent-111", "pageIndex": 2, "pageSize": 5},
    )
    assert response.status_code == 200
    assert response.json()["data"] == {"turns": [], "page_index": 2}
    assert client.fake_agent.turns_calls == [("fake-agent-111", 2, 5)]


def test_agent_turns_unknown_agent_maps_to_400(client):
    assert client.get("/agentTurns", params={"agentId": "unknown-id"}).status_code == 400


def test_value_error_maps_to_400(client, server_module):
    class BadAgent:
        async def start(self, **kwargs):
            raise ValueError("bad input")

        async def stop(self, *args):
            pass

    server_module.agent = BadAgent()
    response = client.post(
        "/startAgent", json={"channelName": "c", "rtcUid": 1, "userUid": 2}
    )
    assert response.status_code == 400
    assert "bad input" in response.json()["detail"]


def test_runtime_error_maps_to_500(client, server_module):
    class BoomAgent:
        async def start(self, **kwargs):
            raise RuntimeError("explode")

        async def stop(self, *args):
            pass

    server_module.agent = BoomAgent()
    response = client.post(
        "/startAgent", json={"channelName": "c", "rtcUid": 1, "userUid": 2}
    )
    assert response.status_code == 500


def test_misconfigured_agent_returns_500(client, server_module):
    server_module.agent = None
    assert client.get("/get_config").status_code == 500
    assert (
        client.post(
            "/startAgent", json={"channelName": "c", "rtcUid": 1, "userUid": 2}
        ).status_code
        == 500
    )
    assert client.post("/stopAgent", json={"agentId": "x"}).status_code == 500
    assert client.post("/interruptAgent", json={"agentId": "x"}).status_code == 500
    assert client.get("/agentHistory", params={"agentId": "x"}).status_code == 500
    assert client.get("/agentTurns", params={"agentId": "x"}).status_code == 500
