
"""Load and validate the MTG taxonomy from a JSON file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .mtg_taxonomy import (
    MTGTaxonomy,
    SubtypeCategory,
    SubtypeCategoryDefinition,
)


class TaxonomyLoadError(ValueError):
    """Raised when a taxonomy file cannot be loaded or validated."""


def load_taxonomy(path: Path) -> MTGTaxonomy:
    """Load an MTG taxonomy from a JSON file."""
    path = Path(path)

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as error:
        raise TaxonomyLoadError(
            f"Invalid JSON in taxonomy file '{path}': {error}"
        ) from error

    if not isinstance(data, dict):
        raise TaxonomyLoadError(
            "The taxonomy root must be a JSON object."
        )

    try:
        return _build_taxonomy(data)
    except (KeyError, TypeError, ValueError) as error:
        raise TaxonomyLoadError(
            f"Invalid taxonomy definition in '{path}': {error}"
        ) from error


def _build_taxonomy(data: dict[str, Any]) -> MTGTaxonomy:
    """Build a taxonomy instance from its JSON representation."""
    _validate_keys(
        data,
        required={
            "metadata",
            "card_types",
            "supertypes",
            "card_types_without_subtypes",
            "subtype_categories",
        },
        context="taxonomy",
    )

    metadata = _require_object(data["metadata"], "metadata")

    _validate_keys(
        metadata,
        required={"rules_version", "rules_effective_date"},
        optional={"source_file"},
        context="metadata",
    )

    categories_data = _require_object(
        data["subtype_categories"],
        "subtype_categories",
    )

    categories: dict[
        SubtypeCategory,
        SubtypeCategoryDefinition,
    ] = {}

    for category_name, definition_data in categories_data.items():
        try:
            category = SubtypeCategory(category_name)
        except ValueError as error:
            raise ValueError(
                f"Unknown subtype category '{category_name}'."
            ) from error

        definition_data = _require_object(
            definition_data,
            f"subtype_categories.{category_name}",
        )

        _validate_keys(
            definition_data,
            required={"card_types", "values"},
            context=f"subtype_categories.{category_name}",
        )

        categories[category] = SubtypeCategoryDefinition(
            category=category,
            card_types=_require_string_list(
                definition_data["card_types"],
                f"subtype_categories.{category_name}.card_types",
            ),
            values=_require_string_list(
                definition_data["values"],
                f"subtype_categories.{category_name}.values",
            ),
        )

    return MTGTaxonomy(
        rules_version=_require_string(
            metadata["rules_version"],
            "metadata.rules_version",
        ),
        rules_effective_date=_require_string(
            metadata["rules_effective_date"],
            "metadata.rules_effective_date",
        ),
        source_file=_require_string(
            metadata.get("source_file", "unknown"),
            "metadata.source_file",
        ),
        card_types=_require_string_list(
            data["card_types"],
            "card_types",
        ),
        supertypes=_require_string_list(
            data["supertypes"],
            "supertypes",
        ),
        card_types_without_subtypes=_require_string_list(
            data["card_types_without_subtypes"],
            "card_types_without_subtypes",
        ),
        subtype_categories=categories,
    )


def _require_object(value: Any, context: str) -> dict[str, Any]:
    """Validate that a value is a JSON object."""
    if not isinstance(value, dict):
        raise TypeError(f"'{context}' must be an object.")

    return value


def _require_string(value: Any, context: str) -> str:
    """Validate that a value is a non-empty string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{context}' must be a non-empty string.")

    return value


def _require_string_list(value: Any, context: str) -> tuple[str, ...]:
    """Validate and convert a JSON string array into a tuple."""
    if not isinstance(value, list):
        raise TypeError(f"'{context}' must be an array.")

    return tuple(
        _require_string(item, f"{context}[{index}]")
        for index, item in enumerate(value)
    )


def _validate_keys(
    data: dict[str, Any],
    *,
    required: set[str],
    context: str,
    optional: set[str] | None = None,
) -> None:
    """Validate required and unexpected keys in a JSON object."""
    optional = optional or set()

    missing = required - data.keys()
    unexpected = data.keys() - required - optional

    if missing:
        raise ValueError(
            f"Missing keys in '{context}': {sorted(missing)}."
        )

    if unexpected:
        raise ValueError(
            f"Unexpected keys in '{context}': {sorted(unexpected)}."
        )
