"""Infrastructure adapters for AI providers.

Concrete provider implementations + the DB-backed resolver. Domain code
imports only the protocols from ``src.domain.ai.providers``; nothing here
should leak into the domain layer.
"""
