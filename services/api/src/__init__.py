"""SilkLens API service.

The single entry point for all HTTP/REST traffic. Bounded contexts live under
``src/domain/<context>``; infrastructure adapters under ``src/infrastructure``;
HTTP routers under ``src/api``. Clean Architecture layering is enforced by
ruff configuration (no domain → infrastructure imports).
"""

__version__ = "0.1.0"
