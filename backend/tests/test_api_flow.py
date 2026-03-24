from time import sleep
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def login_headers(phone: str) -> tuple[dict[str, str], str]:
    send = client.post("/v1/auth/sms/send", json={"phone": phone})
    assert send.status_code == 200
    code = "123456"

    login = client.post("/v1/auth/sms/login", json={"phone": phone, "code": code})
    assert login.status_code == 200
    payload = login.json()
    return {"Authorization": f"Bearer {payload['access_token']}"}, payload["user_id"]


def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["message"] == "ok"


def test_auth_endpoints():
    from app.services.container import auth_service

    auth_service.verify_apple_identity_token = lambda identity_token: SimpleNamespace(  # type: ignore[method-assign]
        subject="apple-user-1",
        email="reviewer@privaterelay.appleid.com",
        email_verified=True,
    )
    auth_service.exchange_apple_authorization_code = lambda authorization_code: SimpleNamespace(  # type: ignore[method-assign]
        refresh_token="refresh-token-1"
    )
    auth_service.revoke_apple_refresh_token = lambda refresh_token: None  # type: ignore[method-assign]

    apple = client.post(
        "/v1/auth/apple-login",
        json={
            "apple_identity_token": "token-12345678",
            "authorization_code": "auth-code-12345678",
            "full_name": "App Review",
        },
    )
    assert apple.status_code == 200
    assert apple.json()["phone"] is None
    assert apple.json()["phone_masked"] is None
    assert apple.json()["has_bound_phone"] is False

    send = client.post("/v1/auth/sms/send", json={"phone": "13800138000"})
    assert send.status_code == 200
    assert send.json()["sent"] is True

    login = client.post("/v1/auth/sms/login", json={"phone": "13800138000", "code": "123456"})
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

    bind_send = client.post("/v1/auth/sms/send", json={"phone": "13800138009"})
    assert bind_send.status_code == 200

    bind = client.post(
        "/v1/auth/phone-bind",
        headers={"Authorization": f"Bearer {apple.json()['access_token']}"},
        json={"phone": "13800138009", "code": "123456"},
    )
    assert bind.status_code == 200
    assert bind.json()["phone"] == "13800138009"
    assert bind.json()["phone_masked"] == "138****8009"
    assert bind.json()["has_bound_phone"] is True

    delete_response = client.delete(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {apple.json()['access_token']}"},
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["success"] is True
    assert delete_response.json()["apple_revoked"] is True

    me_after_delete = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {apple.json()['access_token']}"})
    assert me_after_delete.status_code == 401


def test_session_report_and_billing_flow(monkeypatch):
    headers, _user_id = login_headers("13800138001")

    from app.services.container import billing_service

    monkeypatch.setattr(
        billing_service,
        "verify_signed_transaction",
        lambda signed_transaction_info: SimpleNamespace(
            transaction_id=f"tx-{signed_transaction_info}",
            original_transaction_id=f"orig-{signed_transaction_info}",
            product_id="betweenus.payg.3",
            signed_transaction_info=signed_transaction_info,
            environment="LocalTesting",
            purchase_date_ms=1_710_000_000_000,
            signed_date_ms=1_710_000_000_500,
            revocation_date_ms=None,
            revocation_reason=None,
        ),
    )

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
    assert len(report.json()["action_tasks"]) >= 2
    assert report.json()["transcript_excerpt"]
    assert report.json()["detailed_report"]
    assert "【1. 情绪动态与触发点】" in report.json()["detailed_report"]
    assert "【8." in report.json()["detailed_report"]

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
        json={"signed_transaction_info": "signed-transaction-1"},
    )
    assert iap.status_code == 200
    assert iap.json()["applied"] is True
    assert iap.json()["entitlement"]["payg_units_left"] == 3

    duplicate = client.post(
        "/v1/billing/iap/verify",
        headers=headers,
        json={"signed_transaction_info": "signed-transaction-1"},
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["applied"] is False
    assert duplicate.json()["entitlement"]["payg_units_left"] == 3

    packages = client.get("/v1/billing/packages", headers=headers)
    assert packages.status_code == 200
    assert len(packages.json()) >= 1
    assert {item["package_id"] for item in packages.json()} == {
        "betweenus.payg.1",
        "betweenus.payg.2",
        "betweenus.payg.3",
    }


def test_session_requires_header():
    response = client.post("/v1/sessions", json={"title": "x"})
    assert response.status_code == 401


def test_finish_fails_fast_when_queue_unavailable(monkeypatch):
    headers, _user_id = login_headers("13800138003")

    create = client.post("/v1/sessions", headers=headers, json={"title": "任务队列异常"})
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
    assert finish.status_code == 503
    assert "任务系统暂时不可用" in finish.json()["detail"]

    progress = client.get(f"/v1/sessions/{session_id}/progress", headers=headers)
    assert progress.status_code == 200
    assert progress.json()["stage"] == "failed"

    report = client.get(f"/v1/reports/{session_id}", headers=headers)
    assert report.status_code == 409

    detail = client.get(f"/v1/sessions/{session_id}", headers=headers)
    assert detail.status_code == 200
    assert "任务系统暂时不可用" in detail.json()["failure_reason"]


def test_app_store_notification_updates_order(monkeypatch):
    headers, _user_id = login_headers("13800138004")
    from app.services.container import billing_service

    transaction_map = {
        "signed-payload-paid-1": SimpleNamespace(
            transaction_id="tx-signed-paid",
            original_transaction_id="orig-signed-paid",
            product_id="betweenus.payg.2",
            signed_transaction_info="signed-payload-paid-1",
            environment="LocalTesting",
            purchase_date_ms=1_710_000_000_000,
            signed_date_ms=1_710_000_000_500,
            revocation_date_ms=None,
            revocation_reason=None,
        ),
        "signed-payload-refund-1": SimpleNamespace(
            transaction_id="tx-signed-paid",
            original_transaction_id="orig-signed-paid",
            product_id="betweenus.payg.2",
            signed_transaction_info="signed-payload-refund-1",
            environment="LocalTesting",
            purchase_date_ms=1_710_000_000_000,
            signed_date_ms=1_710_000_001_000,
            revocation_date_ms=1_710_000_100_000,
            revocation_reason=1,
        ),
    }

    monkeypatch.setattr(
        billing_service,
        "verify_signed_transaction",
        lambda signed_transaction_info: transaction_map[signed_transaction_info],
    )
    monkeypatch.setattr(
        billing_service,
        "verify_and_decode_notification",
        lambda signed_payload: SimpleNamespace(
            notification_type="REFUND",
            subtype="",
            signed_transaction_info="signed-payload-refund-1",
        ),
    )

    verify = client.post(
        "/v1/billing/iap/verify",
        headers=headers,
        json={"signed_transaction_info": "signed-payload-paid-1"},
    )
    assert verify.status_code == 200
    assert verify.json()["entitlement"]["payg_units_left"] == 2

    webhook = client.post("/v1/billing/app-store-notifications", json={"signed_payload": "signed-payload-1"})
    assert webhook.status_code == 200
    assert webhook.json()["success"] is True
    assert webhook.json()["applied"] is True

    entitlement = client.get("/v1/billing/entitlements", headers=headers)
    assert entitlement.status_code == 200
    assert entitlement.json()["payg_units_left"] == 0
