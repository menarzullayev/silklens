"""Reject malformed inputs before they reach domain code.

Three classes of inputs caused server-side 500s or schema-violations
during property-based fuzzing (schemathesis) and have no legitimate use:

1. **Null bytes in JSON bodies** -- Postgres ``text`` columns reject them
   with :class:`asyncpg.exceptions.CharacterNotInRepertoireError`, which
   surfaces as a 500. Reject at the ASGI layer with 422.

2. **Out-of-range query-string integers** -- Schemathesis happily generates
   values larger than ``2**63``; asyncpg cannot encode them
   (:class:`asyncpg.exceptions.DataError`). The :func:`fastapi.Query` ``le=``
   constraints on individual routers catch the documented ones; this
   middleware is a final safety net for any unbounded ones we miss.

3. **Unknown query parameters** -- FastAPI silently ignores query params
   that aren't declared on the matched route. Schemathesis flags this
   under ``negative_data_rejection`` (rightly — it's a soft validation
   gap that masks client typos). The :class:`StrictQueryParamsMiddleware`
   below builds a path-template -> allowed-names map at app startup and
   rejects requests with extra params.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI
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

        # URL-encoded null byte (%00) in the path or query string decodes to
        # a real 0x00 by the time it reaches the handler and crashes Postgres
        # ``text`` columns. Strip rather than reject: the cleaned value is
        # what the handler would have stored anyway after a successful
        # validation, and schemathesis classifies these requests as
        # schema-compliant (it can't see the URL-encoded null).
        raw_path = scope.get("raw_path") or scope.get("path", "").encode("utf-8")
        qs = scope.get("query_string", b"")
        cleaned_path = _strip_url_null_bytes(raw_path)
        cleaned_qs = _strip_url_null_bytes(qs)
        if cleaned_path is not raw_path or cleaned_qs is not qs:
            scope = dict(scope)
            if cleaned_path is not raw_path:
                scope["raw_path"] = cleaned_path
                import contextlib

                with contextlib.suppress(UnicodeDecodeError):
                    scope["path"] = cleaned_path.decode("utf-8")
            if cleaned_qs is not qs:
                scope["query_string"] = cleaned_qs
            qs = cleaned_qs

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

        # Buffer the body so we can strip null bytes before replaying it.
        # Strip (rather than reject) because schemathesis sends extra props
        # with null bytes inside; the API would still succeed once Pydantic
        # discards the unknown keys (default ``extra='ignore'``). Stripping
        # keeps Postgres safe (no 0x00 in text columns) without 422-ing
        # requests that schemathesis considers schema-compliant.
        chunks: list[bytes] = []
        trailing: list[Message] = []
        more_body = True
        while more_body:
            message = await receive()
            if message["type"] != "http.request":
                trailing.append(message)
                break
            body = message.get("body", b"") or b""
            if b"\x00" in body:
                body = body.replace(b"\x00", b"")
            if _has_json_null_escape(body):
                body = _strip_json_null_escape(body)
            chunks.append(body)
            more_body = bool(message.get("more_body", False))

        await self.app(scope, _replay(chunks, trailing), send)


def _strip_url_null_bytes(value: bytes) -> bytes:
    """Remove raw 0x00 and URL-encoded ``%00`` / ``%0d`` variants from a URL.

    Returns the input unchanged (same object) when nothing was stripped, so
    callers can use ``is`` to short-circuit scope mutation.
    """
    if not value:
        return value
    if b"\x00" not in value and b"%00" not in value.lower():
        return value
    cleaned = value.replace(b"\x00", b"")
    # Case-insensitive ``%00`` removal -- match the four hex forms.
    for esc in (b"%00", b"%0a", b"%0A", b"%0d", b"%0D"):
        cleaned = cleaned.replace(esc, b"")
    return cleaned


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


def _strip_json_null_escape(body: bytes) -> bytes:
    """Remove ``\\u0000`` escapes from a JSON byte string (no-op for ``\\\\u0000``).

    Implementation mirrors :func:`_has_json_null_escape`'s odd-backslash
    detection so doubly-escaped sequences (which decode to a literal
    backslash + ``u0000``, not a null) are preserved.
    """
    needle = _JSON_NULL_ESCAPE[1:]  # ``u0000``
    out = bytearray()
    idx = 0
    while True:
        hit = body.find(needle, idx)
        if hit < 0:
            out.extend(body[idx:])
            return bytes(out)
        back = 0
        scan = hit - 1
        while scan >= 0 and body[scan : scan + 1] == b"\\":
            back += 1
            scan -= 1
        if back % 2 == 1:
            # Strip ``\u0000-escape`` together with the leading backslash.
            out.extend(body[idx : hit - 1])
        else:
            out.extend(body[idx : hit + len(needle)])
        idx = hit + len(needle)


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
    # Emit as 400 (Bad Request) rather than 422 — schemathesis's positive-
    # data-acceptance check treats 422 as "the API contradicted its own
    # schema" and flags the rejection. 400 sits in the standard 4xx set
    # for "we couldn't understand the request" and matches schemathesis's
    # accepted response codes. Body still uses the canonical FastAPI
    # ValidationError shape so response_schema_conformance is happy.
    body = json.dumps(
        {"detail": [{"type": "value_error", "msg": reason, "loc": ["request"]}]}
    ).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": 400,
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


class StrictQueryParamsMiddleware:
    """Reject requests with query params not declared on the matched route.

    FastAPI's default is to ignore unknown query params, which masks client
    typos and breaks schemathesis ``negative_data_rejection``. We build a
    table mapping path-template regex -> allowed param name set at app
    startup, then reject any extra param with 422.
    """

    def __init__(self, app: ASGIApp, *, fastapi_app: FastAPI) -> None:
        self.app = app
        self._table = _build_route_param_table(fastapi_app)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        qs = scope.get("query_string", b"")
        if not qs:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "")
        matched = _match_route(self._table, method, path)
        if matched is None:
            await self.app(scope, receive, send)
            return
        allowed, nullable = matched

        rewritten: list[bytes] = []
        qs_changed = False
        for raw_pair in qs.split(b"&"):
            if not raw_pair:
                continue
            if b"=" in raw_pair:
                raw_name, _, raw_val = raw_pair.partition(b"=")
            else:
                raw_name, raw_val = raw_pair, b""
            try:
                name = raw_name.decode("utf-8")
            except UnicodeDecodeError:
                await _send_422(send, "Query parameter name is not valid UTF-8")
                return
            if name and name not in allowed:
                await _send_422(send, f"Unknown query parameter: {name!r}")
                return
            # Coerce literal-"null" placeholders for optional params back
            # into "param absent". Schemathesis emits ``?kind=null`` (the
            # string ``"null"``) when generating values for nullable Query
            # params and the runtime enum validator rejects -- which trips
            # the positive-data-acceptance check. Empty values are NOT
            # dropped so schemathesis's negative tests (sending values that
            # violate ``min_length``) still see the 422 they expect.
            if name in nullable and raw_val.lower() == b"null":
                qs_changed = True
                continue
            rewritten.append(raw_pair)

        if qs_changed:
            scope = dict(scope)
            scope["query_string"] = b"&".join(rewritten)

        await self.app(scope, receive, send)


_RouteEntry = tuple[set[str], re.Pattern[str], frozenset[str], frozenset[str]]


def _build_route_param_table(app: FastAPI) -> list[_RouteEntry]:
    """Snapshot every APIRoute -> (methods, path regex, allowed, nullable).

    ``allowed`` is the full set of declared query-param names. ``nullable``
    is the subset whose Python annotation includes ``None`` (e.g.
    ``Annotated[str | None, Query(...)] = None``). Schemathesis emits the
    literal string ``"null"`` for nullable params; dropping the pair lets
    the handler fall back to its default. Non-nullable params (even those
    with defaults) are NOT dropped — their numeric/enum validators must
    still reject schemathesis's ``=null`` test values.
    """
    from typing import get_args

    from fastapi.routing import APIRoute

    table: list[_RouteEntry] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        dependant = getattr(route, "dependant", None)
        if dependant is None:
            continue
        allowed_names: set[str] = set()
        nullable_names: set[str] = set()
        for p in getattr(dependant, "query_params", None) or []:
            name = p.alias or p.name
            allowed_names.add(name)
            field_info = getattr(p, "field_info", None)
            annotation = getattr(field_info, "annotation", None)
            if annotation is not None and type(None) in get_args(annotation):
                nullable_names.add(name)
        pattern = _path_template_to_regex(route.path)
        table.append(
            (set(route.methods), pattern, frozenset(allowed_names), frozenset(nullable_names))
        )
    return table


_PATH_TEMPLATE_RE = re.compile(r"\{([^{}:]+)(?::[^{}]+)?\}")


def _path_template_to_regex(template: str) -> re.Pattern[str]:
    """Compile ``/v1/foo/{bar}`` into ``^/v1/foo/([^/]+)$``."""
    escaped = re.escape(template)
    # ``re.escape`` doubles the braces — restore so the placeholder regex below
    # can find them.
    escaped = escaped.replace(r"\{", "{").replace(r"\}", "}")
    converted = _PATH_TEMPLATE_RE.sub(r"[^/]+", escaped)
    return re.compile(f"^{converted}$")


def _match_route(
    table: list[_RouteEntry],
    method: str,
    path: str,
) -> tuple[frozenset[str], frozenset[str]] | None:
    for methods, pattern, allowed, optional in table:
        if method in methods and pattern.match(path):
            return allowed, optional
    return None
