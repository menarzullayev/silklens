"""Firebase Cloud Messaging push client.

Production: set SILKLENS_FIREBASE_CREDENTIALS_JSON to the content of the
Firebase service account JSON file (from Firebase Console → Project Settings
→ Service Accounts → Generate new private key).

Dev/CI: leave the env var empty → falls back to StubFcmClient (no delivery).

SILK-0059
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Protocol, runtime_checkable

import httpx

from src.core.settings import get_settings

logger = logging.getLogger(__name__)


@runtime_checkable
class PushClient(Protocol):
    async def send(
        self,
        device_token: str,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
        image_url: str | None = None,
    ) -> str | None:
        """Send push to one device. Returns message_id or None on stub."""
        ...

    async def send_multicast(
        self,
        device_tokens: list[str],
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Send to multiple tokens. Returns {success, failure, results}."""
        ...


class StubFcmClient:
    """No-op push client for dev/test — logs but never delivers."""

    async def send(
        self,
        device_token: str,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
        image_url: str | None = None,
    ) -> str | None:
        logger.info(
            "FCM stub: would send '%s' to token %s…",
            title,
            device_token[-8:] if len(device_token) > 8 else "???",
        )
        return None

    async def send_multicast(
        self,
        device_tokens: list[str],
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        logger.info("FCM stub: would send '%s' to %d tokens", title, len(device_tokens))
        return {"success": 0, "failure": 0, "results": []}


class FcmHttpV1Client:
    """FCM HTTP v1 API client using service account JWT auth.

    Does NOT require firebase-admin SDK — pure httpx + manual JWT.
    This avoids a heavy dependency while supporting all FCM v1 features.
    """

    _FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
    _TOKEN_URL = "https://oauth2.googleapis.com/token"
    _FCM_URL_TPL = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"

    def __init__(self, credentials_json: str, project_id: str) -> None:
        self._creds = json.loads(credentials_json)
        self._project_id = project_id or self._creds.get("project_id", "")
        self._access_token: str | None = None
        self._token_expiry: float = 0.0

    async def _get_access_token(self) -> str:
        """Obtain or refresh OAuth2 access token via service account JWT."""
        if self._access_token and time.time() < self._token_expiry - 60:
            return self._access_token

        import base64

        try:
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding
        except ImportError as exc:
            raise RuntimeError(
                "cryptography package required for FCM JWT auth. "
                "Add 'cryptography' to pyproject.toml dependencies."
            ) from exc

        now = int(time.time())
        header = {"alg": "RS256", "typ": "JWT"}
        payload = {
            "iss": self._creds["client_email"],
            "sub": self._creds["client_email"],
            "aud": self._TOKEN_URL,
            "iat": now,
            "exp": now + 3600,
            "scope": self._FCM_SCOPE,
        }

        def _b64(data: dict[str, Any]) -> bytes:
            return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=")

        signing_input = _b64(header) + b"." + _b64(payload)

        from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

        private_key = serialization.load_pem_private_key(
            self._creds["private_key"].encode(),
            password=None,
            backend=default_backend(),
        )
        # Firebase service account keys are RSA — the key union from load_pem
        # would otherwise force us into a wide isinstance ladder for every
        # cryptography algorithm. Narrow once, fail loudly if assumption breaks.
        if not isinstance(private_key, RSAPrivateKey):
            raise TypeError(
                f"Firebase service account key must be RSA, got {type(private_key).__name__}"
            )
        signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
        jwt_token = signing_input + b"." + base64.urlsafe_b64encode(signature).rstrip(b"=")

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                self._TOKEN_URL,
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": jwt_token.decode(),
                },
            )
            resp.raise_for_status()
            token_data = resp.json()

        self._access_token = token_data["access_token"]
        self._token_expiry = now + token_data.get("expires_in", 3600)
        return self._access_token

    def _build_message(
        self,
        device_token: str,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
        image_url: str | None = None,
    ) -> dict[str, Any]:
        notification: dict[str, Any] = {"title": title, "body": body}
        if image_url:
            notification["image"] = image_url

        msg: dict[str, Any] = {
            "token": device_token,
            "notification": notification,
        }
        if data:
            msg["data"] = dict(data)

        return {"message": msg}

    async def send(
        self,
        device_token: str,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
        image_url: str | None = None,
    ) -> str | None:
        token = await self._get_access_token()
        url = self._FCM_URL_TPL.format(project_id=self._project_id)
        payload = self._build_message(device_token, title, body, data, image_url)

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )

        if resp.status_code == 200:
            name = resp.json().get("name")
            return str(name) if name is not None else None

        # 404 = invalid token (deregister it)
        if resp.status_code == 404:
            logger.warning("FCM: invalid token %s…", device_token[-8:])
            return None

        logger.error("FCM send failed %d: %s", resp.status_code, resp.text[:200])
        return None

    async def send_multicast(
        self,
        device_tokens: list[str],
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Send same notification to multiple tokens (sequential, FCM v1 has no batch)."""
        success = 0
        failure = 0
        results = []

        for token in device_tokens:
            msg_id = await self.send(token, title, body, data)
            if msg_id:
                success += 1
                results.append({"token": token[-8:], "message_id": msg_id})
            else:
                failure += 1
                results.append({"token": token[-8:], "error": "invalid_or_failed"})

        return {"success": success, "failure": failure, "results": results}


def get_fcm_client() -> PushClient:
    """Factory: return real FcmHttpV1Client if credentials configured, else StubFcmClient."""
    settings = get_settings()
    creds_json = settings.firebase_credentials_json.get_secret_value()
    project_id = settings.firebase_project_id

    if creds_json and project_id:
        try:
            return FcmHttpV1Client(credentials_json=creds_json, project_id=project_id)
        except Exception as exc:
            logger.warning("FCM: failed to init real client (%s) — falling back to stub", exc)

    return StubFcmClient()
