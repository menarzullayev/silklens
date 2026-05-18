"""AI domain — provider abstraction over vision / text / TTS / translation / embeddings.

The substrate is provider-agnostic by design (Agent 3 §3.1): every concrete
capability is resolved at call time through a ``(provider, model, version)``
triple looked up in ``ai_fallback_chains``. Concrete provider implementations
live under ``src.infrastructure.ai`` so the domain layer stays framework-free.
"""
