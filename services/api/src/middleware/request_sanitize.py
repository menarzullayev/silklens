"""Reject malformed inputs before they reach domain code.

Two classes of inputs caused server-side 500s during property-based fuzzing
(schemathesis) and have no legitimate use:

1. **Null bytes in JSON bodies** -- Postgres ``text`` columns reject them
   with :class:`asyncpg.exceptions.CharacterNotInRepertoireError`, which
   surfaces as a 500. Reject at the ASGI layer with 422.

2. **Out-of-range query-string integers** -- Schemathesis happily generates
   values larger than ``2**63``; asyncpg cannot encode them
   (:class:`asyncpg.exceptions.DataError`). The :func:`fastapi.Query` ``le=``
   constraints on individual routers catch the documented ones; this
   middleware is a final safety net for any unbounded ones we miss.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send


_INT64_MAX = 2**63 - 1

# JSON escape that decodes to a null byte after parsing. Used as bytes for
# fast scanning of the raw request body. Built at runtime to avoid embedding
# the literal byte sequence in source (which would itself contain ``\u0000-escape``
# in a string-literal comment and trip Python's "source code string cannot
# contain null bytes" check).
_JSON_NULL_ESCAPE = b"\\" + b"u" + b"0000"


class RequestSanitizeMiddleware:
    """ASGI middleware: reject null bytes and out-of-range ints with 422."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # URL-encoded null byte (%00) anywhere in the path or query string
        # decodes to a real null byte by the time it reaches the handler and
        # then crashes Postgres ``text`` columns. Reject upfront.
        raw_path = scope.get("raw_path") or scope.get("path", "").encode("utf-8")
        qs = scope.get("query_string", b"")
        for candidate in (raw_path, qs):
            if not candidate:
                continue
            lowered = candidate.lower()
            if b"%00" in lowered or b"\x00" in candidate:
                await _send_422(send, "Null byte in request URL")
                return

        # Reject query-string integers that overflow int64. Postgres BIGINT is
        # signed 64-bit; anything larger crashes asyncpg before the handler runs.
        if qs:
            for raw_pair in qs.split(b"&"):
                if b"=" not in raw_pair:
                    continue
                _, _, raw_val = raw_pair.partition(b"=")
                if not raw_val:
                    continue
                stripped = raw_val.lstrip(b"-")
                if stripped and stripped.isdigit() and len(stripped) > 18:
                    try:
                        if abs(int(raw_val)) > _INT64_MAX:
                            await _send_422(send, "Query integer out of range")
                            return
                    except ValueError:
                        continue

        # Binary uploads (multipart/form-data, octet-stream, image/*, etc.)
        # legitimately contain 0x00 bytes. Only scan textual content types,
        # which is what causes the asyncpg crashes in the first place.
        content_type = _header_value(scope, b"content-type") or b""
        if not _is_textual_content_type(content_type):
            await self.app(scope, receive, send)
            return

        # Buffer the body so we can inspect for null bytes, then replay it.
        # Two encodings to catch: a raw 0x00 byte in the payload, and the
        # JSON escape that decodes to 0x00 after parsing.
        chunks: list[bytes] = []
        trailing: list[Message] = []
        more_body = True
        while more_body:
            message = await receive()
            if message["type"] != "http.request":
                trailing.append(message)
                break
            body = message.get("body", b"") or b""
            if b"\x00" in body or _has_json_null_escape(body):
                await _send_422(send, "Null byte in request body")
                return
            chunks.append(body)
            more_body = bool(message.get("more_body", False))

        await self.app(scope, _replay(chunks, trailing), send)


def _header_value(scope: Scope, name: bytes) -> bytes | None:
    headers = scope.get("headers") or ()
    needle = name.lower()
    for raw_name, raw_value in headers:
        if raw_name.lower() == needle:
            return raw_value
    return None


def _is_textual_content_type(content_type: bytes) -> bool:
    """Return True only for content types we want to sanitize.

    JSON and url-encoded forms reach asyncpg via Postgres ``text`` columns
    and crash on null bytes; multipart/binary uploads bypass that path and
    legitimately carry 0x00 bytes (PNG magic, JPEG markers, etc.).
    """
    if not content_type:
        # No body / empty content-type — nothing to sanitize.
        return False
    primary = content_type.split(b";", 1)[0].strip().lower()
    return primary in (b"application/json", b"application/x-www-form-urlencoded")


def _has_json_null_escape(body: bytes) -> bool:
    """Return True if the body contains an unescaped ``\\u0000`` JSON escape.

    A doubled backslash (``\\\\u0000``) is a literal backslash followed by a
    benign ``u0000``; counting consecutive backslashes immediately before the
    ``u0000`` distinguishes the two cases.
    """
    needle = _JSON_NULL_ESCAPE[1:]  # ``u0000``
    idx = 0
    while True:
        idx = body.find(needle, idx)
        if idx < 0:
            return False
        back = 0
        scan = idx - 1
        while scan >= 0 and body[scan : scan + 1] == b"\\":
            back += 1
            scan -= 1
        if back % 2 == 1:
            return True
        idx += len(needle)


async def _send_422(send: Send, reason: str) -> None:
    body = json.dumps({"detail": [{"type": "value_error", "msg": reason}]}).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": 422,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body, "more_body": False})


def _replay(chunks: list[bytes], trailing: list[Message]) -> Receive:
    """Return a ``receive`` callable that replays the buffered request body."""
    messages: list[Message] = []
    if chunks:
        for i, chunk in enumerate(chunks):
            messages.append(
                {
                    "type": "http.request",
                    "body": chunk,
                    "more_body": i < len(chunks) - 1,
                }
            )
    else:
        messages.append({"type": "http.request", "body": b"", "more_body": False})
    messages.extend(trailing)

    async def receive() -> Message:
        if messages:
            return messages.pop(0)
        return {"type": "http.disconnect"}

    return receive
