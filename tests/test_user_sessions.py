from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import engine
from app.main import app
from app.models_db import UserSessionDB
from app.repositories.users import UserRepository
from app.security import hash_api_key
from app.services.identity_service import IdentityService

client = TestClient(app)
PASSWORD = "EnterprisePass123"
BFF_SECRET = "test-bff-boundary-secret-at-least-32-bytes"


@pytest.fixture(autouse=True)
def _configured_bff_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_BFF_SHARED_SECRET", BFF_SECRET)


def _bff_headers(**extra: str) -> dict[str, str]:
    return {"x-bff-secret": BFF_SECRET, **extra}


def _create_verified_user(*, role: str = "viewer", tenant_id: str | None = None) -> dict:
    suffix = uuid.uuid4().hex
    email = f"session-{suffix}@example.com"
    tenant = tenant_id or f"tenant-{suffix}"
    with Session(engine) as session:
        repo = UserRepository(session)
        identity = IdentityService(repo)
        registered = identity.register(email=email, password=PASSWORD)
        verified = identity.verify_email(registered["verification_token"])
        identity.assign_role(verified["user_id"], tenant, role, assigned_by="test")
    return {"email": email, "user_id": verified["user_id"], "tenant_id": tenant}


def _login(user: dict, **payload: str) -> dict:
    response = client.post(
        "/api/v1/auth/session/login",
        headers=_bff_headers(),
        json={"email": user["email"], "password": PASSWORD, **payload},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_session_token_is_tenant_bound_and_only_digest_is_persisted() -> None:
    user = _create_verified_user(role="editor")
    login = _login(user)
    token = login["session_token"]

    with Session(engine) as session:
        row = session.execute(
            select(UserSessionDB).where(UserSessionDB.id == login["session_id"])
        ).scalar_one()
        assert row.token_hash == hash_api_key(token)
        assert row.token_hash != token
        assert row.tenant_id == user["tenant_id"]
        assert row.role == "editor"

    response = client.get(
        "/api/v1/auth/session",
        headers=_bff_headers(Authorization=f"Bearer {token}"),
    )
    assert response.status_code == 200
    assert response.json()["tenant_id"] == user["tenant_id"]
    assert response.json()["role"] == "editor"
    assert response.headers["cache-control"] == "no-store"


def test_session_rejects_tenant_and_client_role_spoofing() -> None:
    user = _create_verified_user(role="viewer")
    token = _login(user)["session_token"]

    mismatch = client.get(
        "/api/v1/auth/session",
        headers=_bff_headers(
            Authorization=f"Bearer {token}",
            **{"x-tenant-id": "another-tenant"},
        ),
    )
    assert mismatch.status_code == 403

    spoofed = client.post(
        "/api/v1/auth/roles/assign",
        headers={
            "Authorization": f"Bearer {token}",
            "x-opa-user-role": "super_admin",
        },
        json={
            "user_id": user["user_id"],
            "tenant_id": user["tenant_id"],
            "role": "super_admin",
        },
    )
    assert spoofed.status_code == 403


def test_user_session_profile_access_is_self_only() -> None:
    user = _create_verified_user(role="viewer")
    another = _create_verified_user(role="viewer", tenant_id=user["tenant_id"])
    token = _login(user)["session_token"]
    headers = {"Authorization": f"Bearer {token}"}

    own_profile = client.get(f"/api/v1/auth/profile/{user['user_id']}", headers=headers)
    assert own_profile.status_code == 200
    assert own_profile.json()["user_id"] == user["user_id"]

    other_profile = client.get(f"/api/v1/auth/profile/{another['user_id']}", headers=headers)
    assert other_profile.status_code == 403
    other_update = client.put(
        f"/api/v1/auth/profile/{another['user_id']}",
        headers=headers,
        json={"display_name": "Unauthorized"},
    )
    assert other_update.status_code == 403


def test_role_change_and_logout_revoke_sessions() -> None:
    user = _create_verified_user(role="viewer")
    login = _login(user)
    token = login["session_token"]

    with Session(engine) as session:
        UserRepository(session).assign_role(
            user["user_id"], user["tenant_id"], "editor", assigned_by="test"
        )
    changed = client.get(
        "/api/v1/auth/session",
        headers=_bff_headers(Authorization=f"Bearer {token}"),
    )
    assert changed.status_code == 401

    fresh = _login(user)
    logout = client.delete(
        "/api/v1/auth/session",
        headers=_bff_headers(Authorization=f"Bearer {fresh['session_token']}"),
    )
    assert logout.status_code == 204
    revoked = client.get(
        "/api/v1/auth/session",
        headers=_bff_headers(Authorization=f"Bearer {fresh['session_token']}"),
    )
    assert revoked.status_code == 401


def test_password_reset_revokes_all_active_sessions() -> None:
    user = _create_verified_user(role="viewer")
    token = _login(user)["session_token"]
    with Session(engine) as session:
        reset = IdentityService(UserRepository(session)).request_password_reset(user["email"])

    confirmed = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": reset["reset_token"], "new_password": "ChangedPass456"},
    )
    assert confirmed.status_code == 200
    response = client.get(
        "/api/v1/auth/session",
        headers=_bff_headers(Authorization=f"Bearer {token}"),
    )
    assert response.status_code == 401


def test_login_requires_verification_membership_and_explicit_tenant_selection() -> None:
    suffix = uuid.uuid4().hex
    email = f"unverified-{suffix}@example.com"
    with Session(engine) as session:
        IdentityService(UserRepository(session)).register(email=email, password=PASSWORD)
    unverified = client.post(
        "/api/v1/auth/session/login",
        headers=_bff_headers(),
        json={"email": email, "password": PASSWORD},
    )
    assert unverified.status_code == 403
    assert unverified.json()["detail"]["code"] == "email_not_verified"

    user = _create_verified_user(role="viewer")
    second_tenant = f"second-{uuid.uuid4().hex}"
    with Session(engine) as session:
        UserRepository(session).assign_role(
            user["user_id"], second_tenant, "auditor", assigned_by="test"
        )
    selection = client.post(
        "/api/v1/auth/session/login",
        headers=_bff_headers(),
        json={"email": user["email"], "password": PASSWORD},
    )
    assert selection.status_code == 409
    assert selection.json()["detail"]["code"] == "tenant_selection_required"
    assert selection.json()["detail"]["tenants"] == sorted([user["tenant_id"], second_tenant])


def test_bff_shared_secret_is_required_when_configured() -> None:
    user = _create_verified_user()
    response = client.post(
        "/api/v1/auth/session/login",
        json={"email": user["email"], "password": PASSWORD},
    )
    assert response.status_code == 403
