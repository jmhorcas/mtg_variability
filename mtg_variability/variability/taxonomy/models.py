
"""Domain models for the Magic: The Gathering taxonomy."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SubtypeCategory(Enum):
    """Categories of Magic: The Gathering subtypes."""

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
    """Defines a subtype category and its associated card types."""

    name: SubtypeCategory
    card_types: frozenset[str]
    values: frozenset[str]


@dataclass(frozen=True, slots=True)
class SubtypeMatch:
    """Represents a subtype and its possible category associations."""

    value: str
    categories: frozenset[SubtypeCategory]

    @property
    def is_ambiguous(self) -> bool:
        """Whether the subtype belongs to multiple categories."""
        return len(self.categories) > 1
