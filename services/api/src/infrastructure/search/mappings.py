"""Elasticsearch index mappings for SilkLens heritage.

Per Agent 7 §8.2 we ship FIVE indices for FAZA 2:

  Tier-1 (dedicated language analyzers):
    - silklens_heritage_uz    (custom Latin + Cyrillic synonyms)
    - silklens_heritage_en    (Snowball english stemmer)
    - silklens_heritage_ru    (Snowball russian stemmer)
    - silklens_heritage_zh    (smartcn-style — falls back to standard if plugin missing)

  Tier-2 (shared ICU tokenizer + `locale` keyword field):
    - silklens_heritage_intl

Every index carries the same field set so we can move docs between them as
analyzer config evolves. Filter-only fields (kind_slug, country_code, etc.)
are typed as ``keyword`` / numeric — never analysed.
"""

from __future__ import annotations

from typing import Any, Final

# Synonym groups are intentionally short here; the canonical, larger lists
# live in the ``search_synonyms`` admin-managed table per Agent 7 §9.1 and
# will be loaded via ``synonyms_path`` once that admin UI ships.
_UZ_SYNONYMS: Final = [
    "samarqand, samarkand, samarcanda",
    "buxoro, bukhara, bokhara",
    "xiva, khiva, chiwa",
    "registon, registan",
    "madrasa, medresseh, madrassah",
]

# ruff: noqa: RUF001 - mixed Cyrillic + Latin synonym strings are intentional;
# ES synonym graph stays in the analyser's native script per language.
_RU_SYNONYMS: Final = [
    "самарканд, samarqand, samarkand",
    "бухара, buxoro, bukhara",
    "хива, xiva, khiva",
]

_EN_SYNONYMS: Final = [
    "samarkand, samarqand",
    "bukhara, buxoro",
    "khiva, xiva",
    "madrasa, madrassah, medrese",
]


# --- Per-language analyzer blocks -----------------------------------------


def _settings_uz() -> dict[str, Any]:
    return {
        "analysis": {
            "filter": {
                "uz_synonyms": {"type": "synonym_graph", "synonyms": _UZ_SYNONYMS},
                "uz_lowercase": {"type": "lowercase"},
            },
            "analyzer": {
                "uz_text": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["uz_lowercase", "asciifolding", "uz_synonyms"],
                }
            },
        }
    }


def _settings_en() -> dict[str, Any]:
    return {
        "analysis": {
            "filter": {
                "en_synonyms": {"type": "synonym_graph", "synonyms": _EN_SYNONYMS},
                "en_stemmer": {"type": "stemmer", "language": "english"},
                "en_stop": {"type": "stop", "stopwords": "_english_"},
            },
            "analyzer": {
                "en_text": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "asciifolding", "en_stop", "en_stemmer", "en_synonyms"],
                }
            },
        }
    }


def _settings_ru() -> dict[str, Any]:
    return {
        "analysis": {
            "filter": {
                "ru_synonyms": {"type": "synonym_graph", "synonyms": _RU_SYNONYMS},
                "ru_stemmer": {"type": "stemmer", "language": "russian"},
                "ru_stop": {"type": "stop", "stopwords": "_russian_"},
            },
            "analyzer": {
                "ru_text": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "ru_stop", "ru_stemmer", "ru_synonyms"],
                }
            },
        }
    }


def _settings_zh() -> dict[str, Any]:
    # Smartcn would be ideal but isn't always installed in the test cluster;
    # ICU tokenizer covers Han characters reasonably and never throws on
    # the default Elasticsearch distribution.
    return {
        "analysis": {
            "analyzer": {
                "zh_text": {
                    "type": "custom",
                    "tokenizer": "icu_tokenizer",
                    "filter": ["lowercase", "icu_folding"],
                }
            }
        }
    }


def _settings_intl() -> dict[str, Any]:
    return {
        "analysis": {
            "analyzer": {
                "intl_text": {
                    "type": "custom",
                    "tokenizer": "icu_tokenizer",
                    "filter": ["lowercase", "icu_folding"],
                }
            }
        }
    }


def _common_properties(text_analyzer: str, include_locale: bool = False) -> dict[str, Any]:
    props: dict[str, Any] = {
        "heritage_id": {"type": "keyword"},
        "pub_id": {"type": "keyword"},
        "tenant_id": {"type": "keyword"},
        "wikidata_qid": {"type": "keyword"},
        "kind_slug": {"type": "keyword"},
        "country_code": {"type": "keyword"},
        "status": {"type": "keyword"},
        "tags": {"type": "keyword"},
        "lat": {"type": "float"},
        "lng": {"type": "float"},
        "location": {"type": "geo_point"},
        "period_start_year": {"type": "integer"},
        "period_end_year": {"type": "integer"},
        "unesco_inscription_year": {"type": "integer"},
        "confidence_score": {"type": "integer"},
        "revision": {"type": "integer"},
        "updated_at": {"type": "date"},
        "name": {
            "type": "text",
            "analyzer": text_analyzer,
            "fields": {"raw": {"type": "keyword", "ignore_above": 256}},
        },
        "summary_md": {"type": "text", "analyzer": text_analyzer},
        "description_md": {"type": "text", "analyzer": text_analyzer},
        "aliases": {
            "type": "nested",
            "properties": {
                "alias": {"type": "text", "analyzer": text_analyzer},
                "language_tag": {"type": "keyword"},
                "kind": {"type": "keyword"},
            },
        },
        "suggest": {
            "type": "completion",
            "analyzer": "simple",
            "search_analyzer": "simple",
        },
    }
    if include_locale:
        props["locale"] = {"type": "keyword"}
    return props


_HERITAGE_INDEX_NAMES: Final = (
    "silklens_heritage_uz",
    "silklens_heritage_en",
    "silklens_heritage_ru",
    "silklens_heritage_zh",
    "silklens_heritage_intl",
)

HERITAGE_INDICES: Final[frozenset[str]] = frozenset(_HERITAGE_INDEX_NAMES)

TIER1_INDEX_BY_LANG: Final[dict[str, str]] = {
    "uz": "silklens_heritage_uz",
    "en": "silklens_heritage_en",
    "ru": "silklens_heritage_ru",
    "zh": "silklens_heritage_zh",
}

INTL_INDEX: Final = "silklens_heritage_intl"


def mapping_for(index_name: str) -> dict[str, Any]:
    """Return the full create-index body (settings + mappings) for ``index_name``.

    Raises ``KeyError`` for unknown indices to keep the bootstrap loop honest.
    """
    if index_name == "silklens_heritage_uz":
        return {
            "settings": _settings_uz(),
            "mappings": {"properties": _common_properties("uz_text")},
        }
    if index_name == "silklens_heritage_en":
        return {
            "settings": _settings_en(),
            "mappings": {"properties": _common_properties("en_text")},
        }
    if index_name == "silklens_heritage_ru":
        return {
            "settings": _settings_ru(),
            "mappings": {"properties": _common_properties("ru_text")},
        }
    if index_name == "silklens_heritage_zh":
        return {
            "settings": _settings_zh(),
            "mappings": {"properties": _common_properties("zh_text")},
        }
    if index_name == INTL_INDEX:
        return {
            "settings": _settings_intl(),
            "mappings": {"properties": _common_properties("intl_text", include_locale=True)},
        }
    raise KeyError(f"unknown heritage index: {index_name!r}")


def resolve_index(language_tag: str | None) -> str:
    """Map a BCP-47 language tag to the index that owns its docs."""
    if language_tag:
        primary = language_tag.split("-")[0].lower()
        if primary in TIER1_INDEX_BY_LANG:
            return TIER1_INDEX_BY_LANG[primary]
    return INTL_INDEX
