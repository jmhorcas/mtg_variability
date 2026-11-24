
"""Transform extracted MTG data into persistence-ready records."""

from __future__ import annotations

import re
from typing import Any

from mtg_variability.extraction.models import Card, Expansion


ALL_CARD_PROPERTIES = (
    "name",
    "multiverse_id",
    "layout",
    "names",
    "mana_cost",
    "cmc",
    "colors",
    "color_identity",
    "type",
    "supertypes",
    "subtypes",
    "rarity",
    "text",
    "flavor",
    "artist",
    "number",
    "power",
    "toughness",
    "loyalty",
    "variations",
    "watermark",
    "border",
    "timeshifted",
    "hand",
    "life",
    "reserved",
    "release_date",
    "starter",
    "rulings",
    "foreign_names",
    "printings",
    "original_text",
    "original_type",
    "legalities",
    "source",
    "image_url",
    "set",
    "set_name",
    "id",
)

EXPANSION_PROPERTIES = (
    "code",
    "name",
    "gatherer_code",
    "old_code",
    "magic_cards_info_code",
    "release_date",
    "border",
    "type",
    "block",
    "online_only",
    "booster",
    "mkm_id",
    "mkm_name",
)


def is_base_number(number: str | None) -> bool:
    """Return whether a collector number contains only digits."""
    return number is not None and re.fullmatch(r"\d+", number) is not None


def clean_text(value: Any) -> Any:
    """Normalize line breaks and repeated whitespace in text values."""
    if not isinstance(value, str):
        return value

    return re.sub(
        r"\s+",
        " ",
        value.replace("\n", "\\n"),
    ).strip()


def extract_product_features_from_card(card: Card) -> dict[str, Any]:
    """Extract persistence-ready properties from an application Card."""
    return {
        prop: clean_text(card.attributes.get(prop))
        for prop in ALL_CARD_PROPERTIES
    }


def extract_expansion_info(expansion: Expansion) -> dict[str, Any]:
    """Extract persistence-ready properties from an application Expansion."""
    return {
        prop: getattr(expansion, prop, None)
        for prop in EXPANSION_PROPERTIES
    }
