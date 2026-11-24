
"""Domain models and query API for the Magic: The Gathering taxonomy."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping


class SubtypeCategory(StrEnum):
    """Subtype categories defined by the MTG Comprehensive Rules."""

    ARTIFACT = "artifact"
    ENCHANTMENT = "enchantment"
    LAND = "land"
    PLANESWALKER = "planeswalker"
    SPELL = "spell"
    CREATURE = "creature"
    PLANAR = "planar"
    DUNGEON = "dungeon"
    BATTLE = "battle"


@dataclass(frozen=True, slots=True)
class SubtypeCategoryDefinition:
    """Definition of a subtype category and its associated card types."""

    category: SubtypeCategory
    card_types: tuple[str, ...]
    values: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.category, SubtypeCategory):
            raise TypeError("category must be a SubtypeCategory.")

        card_types = tuple(self.card_types)
        values = tuple(self.values)

        _validate_names(card_types, "card types")
        _validate_names(values, f"subtypes in category '{self.category}'")

        object.__setattr__(self, "card_types", card_types)
        object.__setattr__(self, "values", values)


@dataclass(frozen=True, slots=True)
class SubtypeMatch:
    """A subtype and all categories in which it is defined."""

    value: str
    categories: frozenset[SubtypeCategory]

    @property
    def is_ambiguous(self) -> bool:
        """Whether the subtype belongs to multiple categories."""
        return len(self.categories) > 1


@dataclass(frozen=True, slots=True)
class MTGTaxonomy:
    """Immutable representation of an MTG rules taxonomy."""

    rules_version: str
    rules_effective_date: str
    card_types: tuple[str, ...]
    supertypes: tuple[str, ...]
    card_types_without_subtypes: tuple[str, ...]
    subtype_categories: Mapping[
        SubtypeCategory,
        SubtypeCategoryDefinition,
    ]
    source_file: str = ""

    _card_type_lookup: frozenset[str] = field(
        init=False,
        repr=False,
        compare=False,
    )
    _supertype_lookup: frozenset[str] = field(
        init=False,
        repr=False,
        compare=False,
    )
    _subtype_lookup: Mapping[str, SubtypeMatch] = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if not self.rules_version.strip():
            raise ValueError("Rules version cannot be empty.")

        if not self.rules_effective_date.strip():
            raise ValueError("Rules effective date cannot be empty.")

        if not isinstance(self.source_file, str):
            raise TypeError("source_file must be a string.")

        card_types = tuple(self.card_types)
        supertypes = tuple(self.supertypes)
        card_types_without_subtypes = tuple(
            self.card_types_without_subtypes
        )
        categories = dict(self.subtype_categories)

        _validate_names(card_types, "card types")
        _validate_names(supertypes, "supertypes")
        _validate_names(
            card_types_without_subtypes,
            "card types without subtypes",
        )

        if set(categories) != set(SubtypeCategory):
            missing = set(SubtypeCategory) - set(categories)
            unexpected = set(categories) - set(SubtypeCategory)

            raise ValueError(
                "Invalid subtype categories. "
                f"Missing: {sorted(missing)}; "
                f"unexpected: {sorted(unexpected)}."
            )

        card_type_lookup = {
            value.casefold() for value in card_types
        }
        supertype_lookup = {
            value.casefold() for value in supertypes
        }

        categorized_card_types: set[str] = set()
        subtype_categories: dict[str, set[SubtypeCategory]] = {}
        canonical_subtypes: dict[str, str] = {}

        for category, definition in categories.items():
            if definition.category != category:
                raise ValueError(
                    f"Category key '{category}' does not match "
                    f"its definition '{definition.category}'."
                )

            for card_type in definition.card_types:
                normalized = card_type.casefold()

                if normalized not in card_type_lookup:
                    raise ValueError(
                        f"Unknown card type '{card_type}' in "
                        f"subtype category '{category}'."
                    )

                categorized_card_types.add(normalized)

            for value in definition.values:
                key = value.casefold()
                subtype_categories.setdefault(key, set()).add(category)
                canonical_subtypes.setdefault(key, value)

        no_subtype_types = {
            value.casefold()
            for value in card_types_without_subtypes
        }

        unknown_types = no_subtype_types - card_type_lookup

        if unknown_types:
            raise ValueError(
                "Unknown card types declared without subtypes: "
                f"{sorted(unknown_types)}."
            )

        overlap = categorized_card_types & no_subtype_types

        if overlap:
            raise ValueError(
                "Card types cannot both have subtype categories and "
                f"be declared without subtypes: {sorted(overlap)}."
            )

        uncovered = (
            card_type_lookup
            - categorized_card_types
            - no_subtype_types
        )

        if uncovered:
            raise ValueError(
                "Card types not covered by a subtype category or "
                f"the no-subtype declaration: {sorted(uncovered)}."
            )

        subtype_lookup = {
            key: SubtypeMatch(
                value=canonical_subtypes[key],
                categories=frozenset(category_set),
            )
            for key, category_set in subtype_categories.items()
        }

        object.__setattr__(self, "card_types", card_types)
        object.__setattr__(self, "supertypes", supertypes)
        object.__setattr__(
            self,
            "card_types_without_subtypes",
            card_types_without_subtypes,
        )
        object.__setattr__(
            self,
            "subtype_categories",
            MappingProxyType(categories),
        )
        object.__setattr__(
            self,
            "_card_type_lookup",
            frozenset(card_type_lookup),
        )
        object.__setattr__(
            self,
            "_supertype_lookup",
            frozenset(supertype_lookup),
        )
        object.__setattr__(
            self,
            "_subtype_lookup",
            MappingProxyType(subtype_lookup),
        )

    def is_card_type(self, value: str) -> bool:
        """Check whether a value is a recognized card type."""
        return value.casefold() in self._card_type_lookup

    def is_supertype(self, value: str) -> bool:
        """Check whether a value is a recognized supertype."""
        return value.casefold() in self._supertype_lookup

    def get_subtypes(
        self,
        category: SubtypeCategory,
    ) -> tuple[str, ...]:
        """Return all subtypes belonging to a category."""
        if not isinstance(category, SubtypeCategory):
            raise TypeError("category must be a SubtypeCategory.")

        return self.subtype_categories[category].values

    def get_subtype_match(self, value: str) -> SubtypeMatch | None:
        """Find a subtype and return all its possible categories."""
        if not isinstance(value, str):
            raise TypeError("value must be a string.")

        return self._subtype_lookup.get(value.strip().casefold())

    def get_subtype_categories(
        self,
        value: str,
    ) -> frozenset[SubtypeCategory]:
        """Return every category associated with a subtype."""
        match = self.get_subtype_match(value)
        return match.categories if match else frozenset()

    def get_categories_for_card_type(
        self,
        card_type: str,
    ) -> frozenset[SubtypeCategory]:
        """Return subtype categories applicable to a card type."""
        normalized = card_type.casefold()

        return frozenset(
            category
            for category, definition in self.subtype_categories.items()
            if any(
                associated_type.casefold() == normalized
                for associated_type in definition.card_types
            )
        )

    def is_subtype(
        self,
        value: str,
        category: SubtypeCategory | None = None,
    ) -> bool:
        """Check whether a value is a subtype, optionally by category."""
        match = self.get_subtype_match(value)

        if match is None:
            return False

        return category is None or category in match.categories


def _validate_names(values: tuple[str, ...], context: str) -> None:
    """Validate a collection of non-empty, case-insensitively unique names."""
    if not values:
        raise ValueError(f"No values defined for {context}.")

    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError(f"Empty or invalid name in {context}.")

    normalized = [value.casefold() for value in values]

    if len(normalized) != len(set(normalized)):
        raise ValueError(f"Duplicate names in {context}.")
