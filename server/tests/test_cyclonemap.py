"""Tests for Phase 6.2 GET /cycloneMap (plan.md 6.2 map sync).

Mock IMD mode (default) serves data/sample_imd_responses/cyclonetrack_mock.json —
no Agora cloud, no whitelisting needed.
"""


def test_cyclone_map_returns_feature_collection(client):
    response = client.get("/cycloneMap")
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["type"] == "FeatureCollection"
    assert data["cyclone_name"] == "MOCK-01"
    assert "cyclonetrack" in data["source"]
    kinds = {f["properties"]["kind"] for f in data["features"]}
    assert {"position", "track", "cone"} <= kinds


def test_cyclone_map_uses_lon_lat_order(client):
    data = client.get("/cycloneMap").json()["data"]
    point = next(f for f in data["features"] if f["geometry"]["type"] == "Point")
    assert point["geometry"]["coordinates"] == [88.5, 15.2]
    line = next(f for f in data["features"] if f["geometry"]["type"] == "LineString")
    assert line["geometry"]["coordinates"][0] == [87.8, 16.0]
    cone = next(f for f in data["features"] if f["properties"]["kind"] == "cone")
    assert cone["geometry"]["type"] == "Polygon"
    assert cone["geometry"]["coordinates"][0][0] == [88.5, 15.2]


def test_cyclone_geojson_skips_partial_entries(server_module):
    geo = server_module._cyclone_geojson({"data": [{"cyclone_name": "X"}, None, "junk"]})
    assert geo["type"] == "FeatureCollection"
    assert geo["features"] == []
    assert geo["cyclone_name"] == "X"
