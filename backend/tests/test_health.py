def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "version" in data
    assert "server_time" in data
    assert "timezone" in data
