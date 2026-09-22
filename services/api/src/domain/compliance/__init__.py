"""Compliance domain — GDPR + Uzbek PD-law surface.

Owns legal-document publication, consent records, GDPR request lifecycle, and
the anonymization job pipeline. Per ADR-0003 the domain layer is pure Python;
SQL lives in ``src/infrastructure/compliance/repository.py``.
"""
