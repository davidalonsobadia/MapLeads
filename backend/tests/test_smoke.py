"""Smoke tests proving the test harness boots and wires app + auth + DB."""


def test_health_ok(client):
    """The app boots and the public health endpoint responds without an API key."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
