"""AI-domain errors.

Mirrors the heritage-error style (code + status_code on the class). Routers
translate these to HTTP responses; service code raises them on provider
failures, quota exceedance, and prompt-safety blocks.
"""
# ruff: noqa: N818

from __future__ import annotations


class AiError(Exception):
    code: str = "ai.unknown"
    status_code: int = 500


class AiProviderUnavailable(AiError):
    code = "ai.provider_unavailable"
    status_code = 503

    def __init__(self, provider: str, detail: str = "") -> None:
        msg = f"AI provider '{provider}' unavailable"
        if detail:
            msg = f"{msg}: {detail}"
        super().__init__(msg)
        self.provider = provider


class AiQuotaExceeded(AiError):
    code = "ai.quota_exceeded"
    status_code = 429

    def __init__(self, kind: str, *, limit: int) -> None:
        super().__init__(f"AI quota exceeded for '{kind}' (limit={limit})")
        self.kind = kind
        self.limit = limit


class AiPromptBlocked(AiError):
    code = "ai.prompt_blocked"
    status_code = 400

    def __init__(self, score: float) -> None:
        super().__init__(f"Prompt rejected by safety classifier (score={score:.3f})")
        self.score = score


class AiTimeout(AiError):
    code = "ai.timeout"
    status_code = 504


class AiValidationError(AiError):
    code = "ai.validation_failed"
    status_code = 422

    def __init__(self, field: str, reason: str) -> None:
        super().__init__(f"{field}: {reason}")
        self.field = field
        self.reason = reason


class AiConflictError(AiValidationError):
    """Cross-field constraint violation — surfaces as HTTP 409 Conflict.

    Subclasses AiValidationError so ``pytest.raises(AiValidationError)``
    still catches it in tests that only care about the validation aspect.
    Used when two fields are individually valid but mutually incompatible
    (e.g. source_lang == target_lang in a translation request).
    """

    status_code = 409
