import json
from unittest.mock import patch, MagicMock

from app.models import PushSubscription, NotificationLog


def _sub_payload(endpoint="https://push.example.com/sub/1"):
    return {
        "endpoint": endpoint,
        "keys": {"p256dh": "test-p256dh", "auth": "test-auth"},
    }


def test_get_vapid_key(client):
    resp = client.get("/api/push/vapid-public-key")
    assert resp.status_code == 200
    assert "publicKey" in resp.json()


def test_create_subscription(client, db_session):
    resp = client.post("/api/push/subscriptions", json=_sub_payload())
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "active"
    assert data["endpoint"] == "https://push.example.com/sub/1"

    sub = db_session.query(PushSubscription).first()
    assert sub is not None
    assert sub.endpoint == "https://push.example.com/sub/1"


def test_upsert_subscription(client, db_session):
    client.post("/api/push/subscriptions", json=_sub_payload())
    client.post("/api/push/subscriptions", json=_sub_payload())

    count = db_session.query(PushSubscription).count()
    assert count == 1


def test_delete_subscription_marks_expired(client, db_session):
    client.post("/api/push/subscriptions", json=_sub_payload())

    resp = client.request(
        "DELETE",
        "/api/push/subscriptions",
        json={"endpoint": "https://push.example.com/sub/1"},
    )
    assert resp.status_code == 200

    sub = db_session.query(PushSubscription).first()
    assert sub.status == "expired"


def test_delete_nonexistent_returns_404(client):
    resp = client.request(
        "DELETE",
        "/api/push/subscriptions",
        json={"endpoint": "https://push.example.com/no-such"},
    )
    assert resp.status_code == 404


def test_resubscribe_after_expire(client, db_session):
    client.post("/api/push/subscriptions", json=_sub_payload())
    client.request(
        "DELETE",
        "/api/push/subscriptions",
        json={"endpoint": "https://push.example.com/sub/1"},
    )
    resp = client.post("/api/push/subscriptions", json=_sub_payload())
    assert resp.json()["status"] == "active"


@patch("app.services.push.webpush")
def test_send_push_logs_result(mock_webpush, client, db_session):
    client.post("/api/push/subscriptions", json=_sub_payload())

    mock_webpush.return_value = MagicMock()
    resp = client.post("/api/push/test")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["results"] == ["sent"]

    log = db_session.query(NotificationLog).first()
    assert log is not None
    assert log.result == "sent"
    assert log.kind == "test"


@patch("app.services.push.webpush")
def test_push_410_marks_expired(mock_webpush, client, db_session):
    from pywebpush import WebPushException

    mock_resp = MagicMock()
    mock_resp.status_code = 410
    mock_webpush.side_effect = WebPushException("Gone", response=mock_resp)

    client.post("/api/push/subscriptions", json=_sub_payload())
    client.post("/api/push/test")

    sub = db_session.query(PushSubscription).first()
    assert sub.status == "expired"

    log = db_session.query(NotificationLog).first()
    assert log.result == "expired"
