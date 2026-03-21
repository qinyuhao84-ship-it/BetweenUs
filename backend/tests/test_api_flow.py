from fastapi.testclient import TestClient
from time import sleep

from app.main import app


client = TestClient(app)


def login_headers(phone: str) -> tuple[dict[str, str], str]:
    send = client.post("/v1/auth/sms/send", json={"phone": phone})
    assert send.status_code == 200
    code = send.json()["dev_code"]

    login = client.post("/v1/auth/sms/login", json={"phone": phone, "code": code})
    assert login.status_code == 200
    payload = login.json()
    return {"Authorization": f"Bearer {payload['access_token']}"}, payload["user_id"]


def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["message"] == "ok"


def test_runtime_status():
    response = client.get("/v1/system/runtime-status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ai_provider_mode"] in {"auto", "mock", "real"}
    assert isinstance(payload["asr_mock_enabled"], bool)
    assert isinstance(payload["llm_mock_enabled"], bool)


def test_auth_endpoints():
    apple = client.post("/v1/auth/apple-login", json={"apple_identity_token": "token-12345678"})
    assert apple.status_code == 200
    assert apple.json()["user_id"].startswith("u_")
    assert apple.json()["token_type"] == "Bearer"
    assert apple.json()["expires_in_minutes"] > 0
    assert apple.json()["access_token"]

    send = client.post("/v1/auth/sms/send", json={"phone": "13800138000"})
    assert send.status_code == 200
    assert send.json()["sent"] is True
    assert send.json()["dev_code"]

    login = client.post("/v1/auth/sms/login", json={"phone": "13800138000", "code": send.json()["dev_code"]})
    assert login.status_code == 200
    assert login.json()["phone"] == "13800138000"
    assert login.json()["phone_masked"] == "138****8000"
    assert login.json()["user_id"].startswith("u_")
    assert login.json()["access_token"]

    me = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {login.json()['access_token']}"})
    assert me.status_code == 200
    assert me.json()["phone"] == "13800138000"

    update = client.patch(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
        json={"nickname": "小Q"},
    )
    assert update.status_code == 200
    assert update.json()["nickname"] == "小Q"

    bind = client.post("/v1/auth/phone-bind", json={"phone": "13800138000", "code": send.json()["dev_code"]})
    assert bind.status_code == 400


def test_session_report_and_billing_flow():
    headers, _user_id = login_headers("13800138001")

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
    assert finish.json()["status"] in {"processing", "completed"}
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
    assert report.json()["transcript_excerpt"]

    detail = client.get(f"/v1/sessions/{session_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["transcript_excerpt"]

    other_headers, _other_user_id = login_headers("13800138002")
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

    packages = client.get("/v1/billing/packages", headers=headers)
    assert packages.status_code == 200
    assert len(packages.json()) >= 1

    first_package = packages.json()[0]
    create_order = client.post(
        "/v1/billing/payments/create",
        headers=headers,
        json={"package_id": first_package["package_id"], "channel": "alipay"},
    )
    assert create_order.status_code == 200
    order_payload = create_order.json()
    assert order_payload["order_no"].startswith("bu_")
    assert order_payload["status"] == "pending"

    confirm = client.post(
        "/v1/billing/payments/confirm",
        headers=headers,
        json={"order_no": order_payload["order_no"], "provider_order_id": "mock_provider_1"},
    )
    assert confirm.status_code == 200
    assert confirm.json()["applied"] is True
    assert confirm.json()["entitlement"]["payg_units_left"] == 3 + first_package["units"]

    duplicate_confirm = client.post(
        "/v1/billing/payments/confirm",
        headers=headers,
        json={"order_no": order_payload["order_no"], "provider_order_id": "mock_provider_1"},
    )
    assert duplicate_confirm.status_code == 200
    assert duplicate_confirm.json()["applied"] is False
    assert duplicate_confirm.json()["entitlement"]["payg_units_left"] == 3 + first_package["units"]


def test_session_requires_header():
    response = client.post("/v1/sessions", json={"title": "x"})
    assert response.status_code == 401


def test_finish_falls_back_when_queue_unavailable(monkeypatch):
    headers, _user_id = login_headers("13800138003")

    create = client.post("/v1/sessions", headers=headers, json={"title": "降级执行"})
    assert create.status_code == 200
    session_id = create.json()["session_id"]

    upload = client.post(
        f"/v1/sessions/{session_id}/audio",
        headers=headers,
        files={"audio_file": ("demo.m4a", b"fake-audio-bytes", "audio/m4a")},
    )
    assert upload.status_code == 200

    def fake_apply_async(*_args, **_kwargs) -> None:
        raise RuntimeError("queue unavailable")

    monkeypatch.setattr("app.api.v1.endpoints.sessions.process_session_task.apply_async", fake_apply_async)

    finish = client.post(
        f"/v1/sessions/{session_id}/finish",
        headers=headers,
        json={"duration_minutes": 15, "consent_acknowledged": True},
    )
    assert finish.status_code == 200
    assert finish.json()["status"] == "processing"

    progress = None
    for _ in range(30):
        progress = client.get(f"/v1/sessions/{session_id}/progress", headers=headers)
        assert progress.status_code == 200
        if progress.json()["stage"] == "completed":
            break
        sleep(0.1)
    assert progress is not None
    assert progress.json()["stage"] == "completed"

    report = client.get(f"/v1/reports/{session_id}", headers=headers)
    assert report.status_code == 200
