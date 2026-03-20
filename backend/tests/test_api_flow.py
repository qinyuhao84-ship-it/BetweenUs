from fastapi.testclient import TestClient
from time import sleep

from app.main import app


client = TestClient(app)


def login_headers(seed: str) -> tuple[dict[str, str], str]:
    response = client.post("/v1/auth/apple-login", json={"apple_identity_token": seed})
    assert response.status_code == 200
    payload = response.json()
    return {"Authorization": f"Bearer {payload['access_token']}"}, payload["user_id"]


def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["message"] == "ok"


def test_auth_endpoints():
    apple = client.post("/v1/auth/apple-login", json={"apple_identity_token": "token-12345678"})
    assert apple.status_code == 200
    assert apple.json()["user_id"].startswith("u_")
    assert apple.json()["token_type"] == "Bearer"
    assert apple.json()["expires_in_minutes"] > 0
    assert apple.json()["access_token"]

    bind = client.post("/v1/auth/phone-bind", json={"phone": "13800138000", "code": "1234"})
    assert bind.status_code == 200
    assert bind.json()["user_id"].startswith("u_")
    assert bind.json()["access_token"]


def test_session_report_and_billing_flow():
    headers, _user_id = login_headers("seed-demo-a")

    create = client.post("/v1/sessions", headers=headers, json={"title": "今天晚上的争执"})
    assert create.status_code == 200
    session_id = create.json()["session_id"]

    finish_without_audio = client.post(
        f"/v1/sessions/{session_id}/finish",
        headers=headers,
        json={"duration_minutes": 30, "consent_acknowledged": True},
    )
    assert finish_without_audio.status_code == 400

    upload = client.post(
        f"/v1/sessions/{session_id}/audio",
        headers=headers,
        files={"audio_file": ("demo.m4a", b"fake-audio-bytes", "audio/m4a")},
    )
    assert upload.status_code == 200
    assert upload.json()["uploaded"] is True

    denied = client.post(
        f"/v1/sessions/{session_id}/finish",
        headers=headers,
        json={"duration_minutes": 30, "consent_acknowledged": False},
    )
    assert denied.status_code == 400

    finish = client.post(
        f"/v1/sessions/{session_id}/finish",
        headers=headers,
        json={"duration_minutes": 30, "consent_acknowledged": True},
    )
    assert finish.status_code == 200
    assert finish.json()["status"] == "processing"
    assert finish.json()["progress"]["percent"] >= 5

    # Async pipeline should eventually complete.
    progress = None
    for _ in range(12):
        progress = client.get(f"/v1/sessions/{session_id}/progress", headers=headers)
        assert progress.status_code == 200
        if progress.json()["stage"] == "completed":
            break
        sleep(0.1)
    assert progress is not None
    assert progress.json()["stage"] == "completed"

    report = client.get(f"/v1/reports/{session_id}", headers=headers)
    assert report.status_code == 200
    assert len(report.json()["action_tasks"]) == 2

    other_headers, _other_user_id = login_headers("seed-other")
    other_user = client.get(f"/v1/reports/{session_id}", headers=other_headers)
    assert other_user.status_code == 403

    entitlement = client.get("/v1/billing/entitlements", headers=headers)
    assert entitlement.status_code == 200
    assert entitlement.json()["subscription_units_left"] == 5

    iap = client.post(
        "/v1/billing/iap/verify",
        headers=headers,
        json={"product_id": "betweenus.payg.3", "transaction_id": "tx-1"},
    )
    assert iap.status_code == 200
    assert iap.json()["applied"] is True
    assert iap.json()["entitlement"]["payg_units_left"] == 3

    duplicate = client.post(
        "/v1/billing/iap/verify",
        headers=headers,
        json={"product_id": "betweenus.payg.3", "transaction_id": "tx-1"},
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["applied"] is False
    assert duplicate.json()["entitlement"]["payg_units_left"] == 3


def test_session_requires_header():
    response = client.post("/v1/sessions", json={"title": "x"})
    assert response.status_code == 401
