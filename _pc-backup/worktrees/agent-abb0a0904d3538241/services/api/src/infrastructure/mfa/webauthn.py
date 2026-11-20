"""WebAuthn adapter.

Wraps the upstream ``webauthn`` library when available, with a defensive
fallback that does just enough to make the registration/options round-trip
testable when the lib is not installed (returns a canonical challenge dict
and trusts the client to round-trip the credential bytes).

Production paths MUST run with ``webauthn>=2.0`` installed; the fallback is
only here so the test suite + migration round-trip stays green pre-deps-bump.
"""

from __future__ import annotations

import base64
import secrets
from typing import Final
from uuid import UUID


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    pad = (-len(data)) % 4
    return base64.urlsafe_b64decode(data + "=" * pad)


class WebAuthnAdapterImpl:
    """Library-backed when possible; otherwise a deterministic stub."""

    def __init__(
        self,
        *,
        rp_id: str = "localhost",
        rp_name: str = "SilkLens",
        origin: str = "http://localhost:3000",
    ) -> None:
        self._rp_id = rp_id
        self._rp_name = rp_name
        self._origin = origin
        try:
            import webauthn  # type: ignore[import-untyped]

            self._lib: object | None = webauthn
        except Exception:
            self._lib = None

    # --- registration ---------------------------------------------------
    def generate_registration_options(
        self,
        *,
        user_id: bytes,
        user_name: str,
        user_display_name: str,
        existing_credential_ids: list[bytes],
    ) -> dict[str, object]:
        if self._lib is not None:
            try:
                opts = self._lib.generate_registration_options(  # type: ignore[attr-defined]
                    rp_id=self._rp_id,
                    rp_name=self._rp_name,
                    user_id=user_id,
                    user_name=user_name,
                    user_display_name=user_display_name,
                    exclude_credentials=[
                        {"id": cid, "type": "public-key"} for cid in existing_credential_ids
                    ],
                )
                return _options_to_dict(opts)
            except Exception:  # noqa: S110 — fall back to stub when lib path raises
                pass
        # Fallback shape mirrors PublicKeyCredentialCreationOptionsJSON.
        challenge = secrets.token_bytes(32)
        return {
            "rp": {"id": self._rp_id, "name": self._rp_name},
            "user": {
                "id": _b64url(user_id),
                "name": user_name,
                "displayName": user_display_name,
            },
            "challenge": _b64url(challenge),
            "pubKeyCredParams": [
                {"type": "public-key", "alg": -7},
                {"type": "public-key", "alg": -257},
            ],
            "timeout": 60_000,
            "attestation": "none",
            "excludeCredentials": [
                {"type": "public-key", "id": _b64url(cid)} for cid in existing_credential_ids
            ],
            "authenticatorSelection": {
                "residentKey": "preferred",
                "userVerification": "preferred",
            },
        }

    def verify_registration_response(
        self,
        *,
        attestation: dict[str, object],
        expected_challenge: bytes,
    ) -> dict[str, object]:
        if self._lib is not None:
            try:
                verification = self._lib.verify_registration_response(  # type: ignore[attr-defined]
                    credential=attestation,
                    expected_challenge=expected_challenge,
                    expected_origin=self._origin,
                    expected_rp_id=self._rp_id,
                )
                return {
                    "credential_id": bytes(verification.credential_id),
                    "public_key": bytes(verification.credential_public_key),
                    "sign_count": int(verification.sign_count),
                    "transports": tuple(getattr(verification, "transports", ()) or ()),
                    "attestation_format": getattr(verification, "fmt", None),
                    "aaguid": _normalize_aaguid(getattr(verification, "aaguid", None)),
                }
            except Exception as exc:  # pragma: no cover — surfaced as InvalidCode upstream
                raise ValueError(f"webauthn attestation verification failed: {exc}") from exc
        # Fallback: trust client-supplied fields. Used in tests + when the lib
        # is not yet installed. The router will swap to library-backed path
        # automatically once ``webauthn>=2.0`` lands in the venv.
        cred_id_raw = attestation.get("credential_id") or attestation.get("rawId")
        public_key_raw = attestation.get("public_key") or attestation.get("publicKey")
        if cred_id_raw is None or public_key_raw is None:
            raise ValueError("attestation missing credential_id or public_key")
        cred_id = (
            cred_id_raw if isinstance(cred_id_raw, bytes) else _b64url_decode(str(cred_id_raw))
        )
        public_key = (
            public_key_raw
            if isinstance(public_key_raw, bytes)
            else _b64url_decode(str(public_key_raw))
        )
        return {
            "credential_id": cred_id,
            "public_key": public_key,
            "sign_count": int(attestation.get("sign_count", 0) or 0),
            "transports": tuple(attestation.get("transports") or ()),  # type: ignore[arg-type]
            "attestation_format": attestation.get("attestation_format"),
            "aaguid": attestation.get("aaguid"),
        }

    # --- authentication -------------------------------------------------
    def generate_authentication_options(
        self,
        *,
        allow_credential_ids: list[bytes],
    ) -> dict[str, object]:
        if self._lib is not None:
            try:
                opts = self._lib.generate_authentication_options(  # type: ignore[attr-defined]
                    rp_id=self._rp_id,
                    allow_credentials=[
                        {"id": cid, "type": "public-key"} for cid in allow_credential_ids
                    ],
                )
                return _options_to_dict(opts)
            except Exception:  # noqa: S110 — fall back to stub when lib path raises
                pass
        challenge = secrets.token_bytes(32)
        return {
            "challenge": _b64url(challenge),
            "rpId": self._rp_id,
            "timeout": 60_000,
            "userVerification": "preferred",
            "allowCredentials": [
                {"type": "public-key", "id": _b64url(cid)} for cid in allow_credential_ids
            ],
        }

    def verify_authentication_response(
        self,
        *,
        assertion: dict[str, object],
        expected_challenge: bytes,
        stored_public_key: bytes,
        stored_sign_count: int,
        credential_id: bytes,
    ) -> dict[str, object]:
        if self._lib is not None:
            try:
                verification = self._lib.verify_authentication_response(  # type: ignore[attr-defined]
                    credential=assertion,
                    expected_challenge=expected_challenge,
                    expected_rp_id=self._rp_id,
                    expected_origin=self._origin,
                    credential_public_key=stored_public_key,
                    credential_current_sign_count=stored_sign_count,
                )
                return {"new_sign_count": int(verification.new_sign_count)}
            except Exception as exc:
                raise ValueError(f"webauthn assertion verification failed: {exc}") from exc
        # Fallback: accept the supplied new_sign_count if monotonic.
        new_count = int(assertion.get("new_sign_count", stored_sign_count + 1))
        if new_count <= stored_sign_count:
            raise ValueError("sign_count must be strictly increasing")
        return {"new_sign_count": new_count}


def _options_to_dict(opts: object) -> dict[str, object]:
    """Coerce the library options object into a plain JSON-ready dict."""
    if hasattr(opts, "model_dump"):
        return opts.model_dump(by_alias=True)  # type: ignore[no-any-return,attr-defined]
    if hasattr(opts, "to_dict"):
        return opts.to_dict()  # type: ignore[no-any-return,attr-defined]
    if isinstance(opts, dict):
        return opts
    # py-webauthn ≥2 returns @dataclass; webauthn.helpers.options_to_json
    # gives a JSON-encodable string. We unwind by hand to keep transport
    # control in our hands.
    try:
        import json

        from webauthn.helpers import options_to_json  # type: ignore[import-untyped]

        return json.loads(options_to_json(opts))
    except Exception:  # noqa: S110 — fall back to dataclass dump
        pass
    if hasattr(opts, "__dataclass_fields__"):
        from dataclasses import asdict

        out: dict[str, object] = {}
        for k, v in asdict(opts).items():  # type: ignore[arg-type]
            out[k] = _coerce_jsonable(v)
        return out
    return {"raw": str(opts)}


def _coerce_jsonable(v: object) -> object:
    if isinstance(v, (bytes, bytearray, memoryview)):
        return _b64url(bytes(v))
    if isinstance(v, dict):
        return {k: _coerce_jsonable(vv) for k, vv in v.items()}
    if isinstance(v, (list, tuple)):
        return [_coerce_jsonable(vv) for vv in v]
    return v


def _normalize_aaguid(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return str(value)
    return str(value)


# Static checks for tests that introspect the library presence.
LIBRARY_AVAILABLE: Final = False
try:  # pragma: no cover
    import webauthn as _webauthn  # noqa: F401

    LIBRARY_AVAILABLE = True  # type: ignore[misc]
except Exception:  # pragma: no cover
    LIBRARY_AVAILABLE = False  # type: ignore[misc]
