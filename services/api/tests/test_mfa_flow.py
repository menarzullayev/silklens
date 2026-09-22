"""End-to-end tests for the MFA login gate (login → challenge → verify). SILK-0063.

These tests are DB-backed integration tests that exercise the complete flow:
  1. Register a user and enroll TOTP.
  2. Attempt login → 401 + challenge_id.
  3. Verify with the correct TOTP code → full LoginResponse (access + refresh + user).
  4. Verify with a wrong code → 422 identity.mfa_invalid_code.

Run with ``make api-test`` (requires the dev stack).
"""

from __future__ import annotations

import uuid

import pyotp
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


def _unique_email() -> str:
    return f"mfa-flow-{uuid.uuid4().hex[:10]}@silklens-test.com"


def _strong_password() -> str:
    return "SilkLensMfaFlow1234"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _register_and_enroll_totp(http: AsyncClient) -> tuple[str, str, str, str]:
    """Register, enroll TOTP, activate it. Returns (email, password, secret, access_token)."""
    email = _unique_email()
    pwd = _strong_password()

    reg = await http.post("/v1/auth/register", json={"email": email, "password": pwd})
    assert reg.status_code == 201, reg.text
    token = reg.json()["tokens"]["access_token"]

    enroll = await http.post(
        "/v1/me/mfa/totp/enroll", json={"label": "phone"}, headers=_auth(token)
    )
    assert enroll.status_code == 201, enroll.text
    body = enroll.json()
    secret = body["secret_base32"]
    mfa_id = body["mfa_id"]

    code = pyotp.TOTP(secret).now()
    verify_enroll = await http.post(
        "/v1/me/mfa/totp/verify-enrollment",
        json={"mfa_id": mfa_id, "code": code},
        headers=_auth(token),
    )
    assert verify_enroll.status_code == 200, verify_enroll.text
    assert verify_enroll.json()["status"] == "active"

    return email, pwd, secret, token


# ---------------------------------------------------------------------------
# 1. Login gate: user with TOTP enrolled → 401 + challenge_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mfa_login_gate_returns_401_with_challenge(http: AsyncClient) -> None:
    """Login with TOTP-enrolled user returns 401 and a usable challenge_id."""
    email, pwd, _secret, _token = await _register_and_enroll_totp(http)

    resp = await http.post("/v1/auth/login", json={"email": email, "password": pwd})

    assert resp.status_code == 401, resp.text
    detail = resp.json()["detail"]
    assert detail["code"] == "identity.mfa_required"
    assert detail["message"] == "MFA challenge required to complete login"
    assert "challenge_id" in detail
    assert uuid.UUID(detail["challenge_id"])  # parseable UUID
    assert "totp" in detail["available_methods"]


# ---------------------------------------------------------------------------
# 2. Verify with correct TOTP → full session (access + refresh + user)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mfa_verify_correct_code_issues_full_session(http: AsyncClient) -> None:
    """After login gate → verify with correct TOTP returns access+refresh+user."""
    email, pwd, secret, _token = await _register_and_enroll_totp(http)

    login = await http.post("/v1/auth/login", json={"email": email, "password": pwd})
    assert login.status_code == 401, login.text
    challenge_id = login.json()["detail"]["challenge_id"]

    verify_code = pyotp.TOTP(secret).now()
    verify = await http.post(
        "/v1/auth/mfa/verify",
        json={"challenge_id": challenge_id, "method": "totp", "code": verify_code},
    )
    assert verify.status_code == 200, verify.text
    body = verify.json()

    # Access token with mfa=true claim
    assert body["mfa"] is True
    assert body["access_token"]

    # Full session: refresh token issued
    assert body["refresh_token"] is not None, "login-gate verify must include a refresh token"
    assert body["expires_in"] is not None

    # User object populated
    assert body["user"] is not None
    user = body["user"]
    assert user["id"]
    assert user["pub_id"]
    assert user["tenant_id"]
    assert user["trust_tier"]


# ---------------------------------------------------------------------------
# 3. Verify with wrong TOTP code → 422
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mfa_verify_wrong_code_returns_422(http: AsyncClient) -> None:
    """Verify with an incorrect TOTP code returns 422 identity.mfa_invalid_code."""
    email, pwd, _secret, _token = await _register_and_enroll_totp(http)

    login = await http.post("/v1/auth/login", json={"email": email, "password": pwd})
    assert login.status_code == 401, login.text
    challenge_id = login.json()["detail"]["challenge_id"]

    resp = await http.post(
        "/v1/auth/mfa/verify",
        json={"challenge_id": challenge_id, "method": "totp", "code": "000000"},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["code"] == "identity.mfa_invalid_code"


# ---------------------------------------------------------------------------
# 4. Refresh token from MFA verify can be used to refresh session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mfa_verify_refresh_token_is_usable(http: AsyncClient) -> None:
    """The refresh token issued after MFA verify works with /v1/auth/refresh."""
    email, pwd, secret, _token = await _register_and_enroll_totp(http)

    login = await http.post("/v1/auth/login", json={"email": email, "password": pwd})
    challenge_id = login.json()["detail"]["challenge_id"]

    verify_code = pyotp.TOTP(secret).now()
    verify = await http.post(
        "/v1/auth/mfa/verify",
        json={"challenge_id": challenge_id, "method": "totp", "code": verify_code},
    )
    assert verify.status_code == 200, verify.text
    refresh_token = verify.json()["refresh_token"]

    refresh_resp = await http.post("/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_resp.status_code == 200, refresh_resp.text
    assert refresh_resp.json()["tokens"]["access_token"]
    assert refresh_resp.json()["user"]["id"]


# ---------------------------------------------------------------------------
# 5. Pure step-up challenge (created via /auth/mfa/challenge) still returns
#    no refresh token — the step-up path is unchanged.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step_up_challenge_verify_no_refresh_token(http: AsyncClient) -> None:
    """Manually created challenge (step-up) returns no refresh token after verify."""
    _email, _pwd, secret, token = await _register_and_enroll_totp(http)

    # Fetch the user ID from /v1/auth/me
    me = await http.get("/v1/auth/me", headers=_auth(token))
    assert me.status_code == 200, me.text
    user_id = me.json()["user"]["id"]

    # Manually create a step-up challenge (not via login gate)
    challenge_r = await http.post(
        "/v1/auth/mfa/challenge", json={"user_id": user_id, "method": "totp"}
    )
    assert challenge_r.status_code == 201, challenge_r.text
    challenge_id = challenge_r.json()["challenge_id"]

    verify_code = pyotp.TOTP(secret).now()
    verify = await http.post(
        "/v1/auth/mfa/verify",
        json={"challenge_id": challenge_id, "method": "totp", "code": verify_code},
    )
    assert verify.status_code == 200, verify.text
    body = verify.json()

    # Step-up token present, but no refresh token and no user object (step-up only)
    assert body["mfa"] is True
    assert body["access_token"]
    assert body["refresh_token"] is None
    assert body["user"] is None
