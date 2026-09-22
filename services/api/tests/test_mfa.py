"""End-to-end MFA tests.

Covers:
- TOTP enroll + verify round-trip
- Wrong TOTP code is rejected
- Backup codes generate + single-use
- WebAuthn registration challenge shape
- Login-with-MFA returns 401 + challenge_id
- MFA verify returns elevated tokens with mfa=true claim
- Step-up gating on account deletion + disable_method
"""

from __future__ import annotations

import secrets
import uuid

import jwt
import pyotp
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.settings import get_settings
from src.infrastructure.mfa.totp import current_totp

pytestmark = pytest.mark.integration


def _unique_email() -> str:
    return f"mfa-{uuid.uuid4().hex[:10]}@silklens-test.com"


def _strong_password() -> str:
    return "SilkLensMfaPwd1234"


async def _register(http: AsyncClient) -> tuple[str, str, str, dict]:
    email = _unique_email()
    pwd = _strong_password()
    r = await http.post("/v1/auth/register", json={"email": email, "password": pwd})
    assert r.status_code == 201, r.text
    body = r.json()
    return email, pwd, body["tokens"]["access_token"], body["user"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# --- TOTP enrollment --------------------------------------------------------


@pytest.mark.asyncio
async def test_totp_enroll_returns_provisioning_uri(http: AsyncClient) -> None:
    _, _, token, _ = await _register(http)
    r = await http.post("/v1/me/mfa/totp/enroll", json={"label": "phone"}, headers=_auth(token))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["mfa_id"]
    assert body["secret_base32"]
    assert body["provisioning_uri"].startswith("otpauth://totp/")


@pytest.mark.asyncio
async def test_totp_verify_round_trip_activates_method(http: AsyncClient) -> None:
    _, _, token, _ = await _register(http)
    enroll = (
        await http.post("/v1/me/mfa/totp/enroll", json={"label": "phone"}, headers=_auth(token))
    ).json()
    secret = enroll["secret_base32"]
    code = pyotp.TOTP(secret).now()
    r = await http.post(
        "/v1/me/mfa/totp/verify-enrollment",
        json={"mfa_id": enroll["mfa_id"], "code": code},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "active"


@pytest.mark.asyncio
async def test_totp_verify_with_wrong_code_returns_422(http: AsyncClient) -> None:
    _, _, token, _ = await _register(http)
    enroll = (
        await http.post("/v1/me/mfa/totp/enroll", json={"label": "phone"}, headers=_auth(token))
    ).json()
    r = await http.post(
        "/v1/me/mfa/totp/verify-enrollment",
        json={"mfa_id": enroll["mfa_id"], "code": "000000"},
        headers=_auth(token),
    )
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["code"] == "identity.mfa_invalid_code"


# --- Listing ----------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_methods_after_totp_enrollment(http: AsyncClient) -> None:
    _, _, token, _ = await _register(http)
    enroll = (
        await http.post("/v1/me/mfa/totp/enroll", json={"label": "phone"}, headers=_auth(token))
    ).json()
    code = pyotp.TOTP(enroll["secret_base32"]).now()
    await http.post(
        "/v1/me/mfa/totp/verify-enrollment",
        json={"mfa_id": enroll["mfa_id"], "code": code},
        headers=_auth(token),
    )
    r = await http.get("/v1/me/mfa", headers=_auth(token))
    assert r.status_code == 200, r.text
    methods = r.json()["methods"]
    assert any(m["method"] == "totp" and m["status"] == "active" for m in methods)


# --- Backup codes -----------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_backup_codes_returns_10_unique_codes(http: AsyncClient) -> None:
    _, _, token, _ = await _register(http)
    r = await http.post("/v1/me/mfa/backup-codes/generate", headers=_auth(token))
    assert r.status_code == 201, r.text
    codes = r.json()["codes"]
    assert len(codes) == 10
    assert len(set(codes)) == 10
    for code in codes:
        assert len(code) == 12


@pytest.mark.asyncio
async def test_backup_code_single_use(http: AsyncClient, db_session: AsyncSession) -> None:
    _, _, token, user = await _register(http)
    user_id = user["id"]
    gen = (await http.post("/v1/me/mfa/backup-codes/generate", headers=_auth(token))).json()
    code = gen["codes"][0]

    # Initiate a backup_codes challenge for the user.
    challenge_r = await http.post(
        "/v1/auth/mfa/challenge",
        json={"user_id": user_id, "method": "backup_codes"},
    )
    assert challenge_r.status_code == 201, challenge_r.text
    challenge_id = challenge_r.json()["challenge_id"]

    # First use → success.
    v1 = await http.post(
        "/v1/auth/mfa/verify",
        json={"challenge_id": challenge_id, "method": "backup_codes", "code": code},
    )
    assert v1.status_code == 200, v1.text
    assert v1.json()["mfa"] is True

    # Second challenge with the same code must fail (single-use).
    challenge2 = (
        await http.post(
            "/v1/auth/mfa/challenge",
            json={"user_id": user_id, "method": "backup_codes"},
        )
    ).json()
    v2 = await http.post(
        "/v1/auth/mfa/verify",
        json={
            "challenge_id": challenge2["challenge_id"],
            "method": "backup_codes",
            "code": code,
        },
    )
    assert v2.status_code == 422
    assert v2.json()["detail"]["code"] == "identity.mfa_invalid_code"


# --- Login flow with MFA enrolled -----------------------------------------


@pytest.mark.asyncio
async def test_login_with_totp_enrolled_returns_mfa_required(http: AsyncClient) -> None:
    email, pwd, token, _ = await _register(http)
    enroll = (
        await http.post("/v1/me/mfa/totp/enroll", json={"label": "phone"}, headers=_auth(token))
    ).json()
    code = pyotp.TOTP(enroll["secret_base32"]).now()
    await http.post(
        "/v1/me/mfa/totp/verify-enrollment",
        json={"mfa_id": enroll["mfa_id"], "code": code},
        headers=_auth(token),
    )
    # Now login → expect 401 mfa_required.
    login = await http.post("/v1/auth/login", json={"email": email, "password": pwd})
    assert login.status_code == 401, login.text
    detail = login.json()["detail"]
    assert detail["code"] == "identity.mfa_required"
    assert detail["challenge_id"]
    assert "totp" in detail["available_methods"]


@pytest.mark.asyncio
async def test_mfa_verify_returns_elevated_token_with_mfa_claim(http: AsyncClient) -> None:
    email, pwd, token, _ = await _register(http)
    enroll = (
        await http.post("/v1/me/mfa/totp/enroll", json={"label": "phone"}, headers=_auth(token))
    ).json()
    secret = enroll["secret_base32"]
    code = pyotp.TOTP(secret).now()
    await http.post(
        "/v1/me/mfa/totp/verify-enrollment",
        json={"mfa_id": enroll["mfa_id"], "code": code},
        headers=_auth(token),
    )
    # Trigger login → mfa_required → grab challenge_id → verify with fresh code.
    login = await http.post("/v1/auth/login", json={"email": email, "password": pwd})
    challenge_id = login.json()["detail"]["challenge_id"]

    verify_code = pyotp.TOTP(secret).now()
    verify = await http.post(
        "/v1/auth/mfa/verify",
        json={"challenge_id": challenge_id, "method": "totp", "code": verify_code},
    )
    assert verify.status_code == 200, verify.text
    body = verify.json()
    assert body["mfa"] is True
    access = body["access_token"]
    settings = get_settings()
    claims = jwt.decode(
        access,
        settings.jwt_secret.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
    )
    assert claims["mfa"] is True


# --- WebAuthn smoke --------------------------------------------------------


@pytest.mark.asyncio
async def test_webauthn_registration_options_shape(http: AsyncClient) -> None:
    _, _, token, _ = await _register(http)
    r = await http.post(
        "/v1/me/mfa/webauthn/begin-registration",
        json={"label": "yubi"},
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["challenge_id"]
    options = body["options"]
    # PublicKeyCredentialCreationOptions canonical fields. The webauthn lib's
    # serializer uses lowerCamelCase; the fallback uses the same.
    keys = set(options.keys())
    assert ("rp" in keys) or ("rpId" in keys)
    assert ("challenge" in keys) or ("challengeBase64Url" in keys)
    assert (
        ("pubKeyCredParams" in keys)
        or ("pub_key_cred_params" in keys)
        or ("publicKeyCredParams" in keys)
    )


# --- Step-up gating --------------------------------------------------------


@pytest.mark.asyncio
async def test_account_delete_blocked_when_step_up_stale(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    _, _, token, user = await _register(http)
    enroll = (
        await http.post("/v1/me/mfa/totp/enroll", json={"label": "phone"}, headers=_auth(token))
    ).json()
    code = pyotp.TOTP(enroll["secret_base32"]).now()
    await http.post(
        "/v1/me/mfa/totp/verify-enrollment",
        json={"mfa_id": enroll["mfa_id"], "code": code},
        headers=_auth(token),
    )
    # Force last_mfa_at into the past so the step-up gate fires.
    await db_session.execute(
        text(
            "UPDATE users SET last_mfa_at = now() - interval '1 hour' "
            "WHERE id = :id AND residency_region = :r"
        ),
        {"id": uuid.UUID(user["id"]), "r": user["residency_region"]},
    )
    await db_session.commit()

    r = await http.post(
        "/v1/me/account/delete",
        json={"reason": "test"},
        headers=_auth(token),
    )
    assert r.status_code == 403, r.text
    assert r.json()["detail"]["code"] == "identity.mfa_step_up_required"


@pytest.mark.asyncio
async def test_disable_method_requires_step_up_when_stale(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    _, _, token, user = await _register(http)
    enroll = (
        await http.post("/v1/me/mfa/totp/enroll", json={"label": "phone"}, headers=_auth(token))
    ).json()
    code = pyotp.TOTP(enroll["secret_base32"]).now()
    activate = await http.post(
        "/v1/me/mfa/totp/verify-enrollment",
        json={"mfa_id": enroll["mfa_id"], "code": code},
        headers=_auth(token),
    )
    mfa_id = activate.json()["id"]
    # Stale the clock.
    await db_session.execute(
        text(
            "UPDATE users SET last_mfa_at = now() - interval '1 hour' "
            "WHERE id = :id AND residency_region = :r"
        ),
        {"id": uuid.UUID(user["id"]), "r": user["residency_region"]},
    )
    await db_session.commit()

    r = await http.delete(f"/v1/me/mfa/{mfa_id}", headers=_auth(token))
    assert r.status_code == 403, r.text
    assert r.json()["detail"]["code"] == "identity.mfa_step_up_required"


@pytest.mark.asyncio
async def test_account_delete_succeeds_for_user_without_mfa(http: AsyncClient) -> None:
    """Step-up's ``allow_first_setup=True`` lets non-MFA users still self-delete."""
    _, _, token, _ = await _register(http)
    r = await http.post(
        "/v1/me/account/delete",
        json={"reason": "test"},
        headers=_auth(token),
    )
    assert r.status_code == 202, r.text


# --- Challenge expiry / replay -------------------------------------------


@pytest.mark.asyncio
async def test_unknown_challenge_returns_404(http: AsyncClient) -> None:
    r = await http.post(
        "/v1/auth/mfa/verify",
        json={
            "challenge_id": str(uuid.uuid4()),
            "method": "totp",
            "code": "123456",
        },
    )
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "identity.mfa_challenge_not_found"


@pytest.mark.asyncio
async def test_expired_challenge_rejected(http: AsyncClient, db_session: AsyncSession) -> None:
    email, pwd, token, _ = await _register(http)
    enroll = (
        await http.post("/v1/me/mfa/totp/enroll", json={"label": "phone"}, headers=_auth(token))
    ).json()
    secret = enroll["secret_base32"]
    code = pyotp.TOTP(secret).now()
    await http.post(
        "/v1/me/mfa/totp/verify-enrollment",
        json={"mfa_id": enroll["mfa_id"], "code": code},
        headers=_auth(token),
    )
    login = await http.post("/v1/auth/login", json={"email": email, "password": pwd})
    challenge_id = login.json()["detail"]["challenge_id"]
    # Force expiry.
    await db_session.execute(
        text("UPDATE mfa_challenges SET expires_at = now() - interval '1 hour' WHERE id = :cid"),
        {"cid": uuid.UUID(challenge_id)},
    )
    await db_session.commit()

    verify_code = pyotp.TOTP(secret).now()
    r = await http.post(
        "/v1/auth/mfa/verify",
        json={"challenge_id": challenge_id, "method": "totp", "code": verify_code},
    )
    assert r.status_code == 410, r.text
    assert r.json()["detail"]["code"] == "identity.mfa_challenge_expired"


# --- TOTP infrastructure helper -------------------------------------------


def test_current_totp_helper_matches_pyotp() -> None:
    """Sanity check that the stdlib fallback's current_totp() matches pyotp."""
    secret = pyotp.random_base32()
    assert current_totp(secret) == pyotp.TOTP(secret).now()


# --- Permission seeded ----------------------------------------------------


@pytest.mark.asyncio
async def test_mfa_bypass_permission_seeded(db_session: AsyncSession) -> None:
    """Migration 0084 seeds the ``mfa:bypass_for_user`` permission and grants
    it to ``super_admin``."""
    granted = (
        await db_session.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM role_permissions rp
                    JOIN roles r ON r.id = rp.role_id
                    JOIN permissions p ON p.id = rp.permission_id
                    WHERE r.slug = 'super_admin' AND p.slug = 'mfa:bypass_for_user'
                )
                """
            )
        )
    ).scalar_one()
    assert granted is True
    not_in_other = (
        await db_session.execute(
            text(
                """
                SELECT COUNT(*) FROM role_permissions rp
                JOIN roles r ON r.id = rp.role_id
                JOIN permissions p ON p.id = rp.permission_id
                WHERE r.slug <> 'super_admin' AND p.slug = 'mfa:bypass_for_user'
                """
            )
        )
    ).scalar_one()
    assert not_in_other == 0


# --- Pgcrypto round-trip ---------------------------------------------------


@pytest.mark.asyncio
async def test_totp_secret_is_encrypted_at_rest(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    """The on-disk ``secret_bytes`` must not equal the plaintext secret."""
    _, _, token, _ = await _register(http)
    enroll = (
        await http.post("/v1/me/mfa/totp/enroll", json={"label": "phone"}, headers=_auth(token))
    ).json()
    secret_plain = enroll["secret_base32"]
    raw = (
        await db_session.execute(
            text("SELECT secret_bytes FROM mfa_totp_secrets WHERE mfa_id = :id"),
            {"id": uuid.UUID(enroll["mfa_id"])},
        )
    ).scalar_one()
    assert secret_plain.encode("utf-8") not in bytes(raw)


# --- Helper / placeholder for future webauthn finish ----------------------


@pytest.mark.asyncio
async def test_webauthn_finish_rejects_garbage_attestation(http: AsyncClient) -> None:
    _, _, token, _ = await _register(http)
    begin = (
        await http.post(
            "/v1/me/mfa/webauthn/begin-registration",
            json={"label": "yubi"},
            headers=_auth(token),
        )
    ).json()
    r = await http.post(
        "/v1/me/mfa/webauthn/finish-registration",
        json={
            "challenge_id": begin["challenge_id"],
            "attestation": {"id": secrets.token_urlsafe(8)},
        },
        headers=_auth(token),
    )
    assert r.status_code in (400, 422)
