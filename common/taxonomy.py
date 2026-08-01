"""Shared category/place normalization for articles and clusters."""

from __future__ import annotations

import unicodedata

ALLOWED_CATEGORIES = (
    "Política",
    "Economía",
    "Clima",
    "Tecnología",
    "Sociedad",
    "Cultura",
)
DEFAULT_CATEGORY = "Sociedad"
DEFAULT_PLACE = "Nacional"


def _fold_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_text.casefold().strip()


_CATEGORY_LOOKUP = {_fold_key(name): name for name in ALLOWED_CATEGORIES}


def normalize_category(value: str | None) -> str:
    text = (value or "").strip()
    if not text:
        return DEFAULT_CATEGORY
    return _CATEGORY_LOOKUP.get(_fold_key(text), DEFAULT_CATEGORY)


def normalize_place(value: str | None) -> str:
    text = " ".join((value or "").split())
    if not text:
        return DEFAULT_PLACE.upper()
    return text.upper()
