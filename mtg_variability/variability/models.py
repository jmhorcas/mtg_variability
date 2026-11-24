
"""Domain models for variability analysis.

These models represent the variability discovered in an expansion,
independently of any feature-modeling framework.
"""

from __future__ import annotations

from enum import StrEnum
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any


class VariabilityCategory(StrEnum):
    """Categories of variability represented in a specification."""

    FUNCTIONAL = "functional"
    COLLECTION = "collection"
    PRESENTATION = "presentation"


@dataclass(frozen=True, slots=True)
class VariantSpec:
    """A concrete variant observed for a variation point.

    A variant may introduce additional variation points that are only
    applicable when that variant is considered.

    Examples:
        Creature
        Artifact
        Human
        Legendary
        3
        Mythic Rare
    """

    name: str
    occurrences: int = 0
    child_points: tuple[VariationPointSpec, ...] = ()
    examples: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("A variant name cannot be empty.")

        if self.occurrences < 0:
            raise ValueError("Variant occurrences cannot be negative.")

        object.__setattr__(self, "child_points", tuple(self.child_points))
        object.__setattr__(self, "examples", tuple(self.examples))
        object.__setattr__(self, "metadata", dict(self.metadata))


@dataclass(frozen=True, slots=True)
class VariationPointSpec:
    """A dimension of variability discovered in the dataset.

    A variation point contains observed variants and can also contain
    subordinate variation points that apply independently of a specific
    variant.

    Variant-specific variation points are represented by the
    ``child_points`` attribute of VariantSpec.

    Examples:
        Type line
        Type
        SuperType
        Creature Subtypes
        Power
        Toughness
    """

    name: str
    source_attributes: tuple[str, ...] = ()
    variants: tuple[VariantSpec, ...] = ()
    child_points: tuple[VariationPointSpec, ...] = ()
    total_observations: int = 0
    missing_observations: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)
    category: VariabilityCategory = VariabilityCategory.FUNCTIONAL

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("A variation point name cannot be empty.")

        if self.total_observations < 0:
            raise ValueError("Total observations cannot be negative.")

        if self.missing_observations < 0:
            raise ValueError("Missing observations cannot be negative.")

        if self.missing_observations > self.total_observations:
            raise ValueError(
                "Missing observations cannot exceed total observations."
            )

        source_attributes = tuple(self.source_attributes)

        if any(not attribute.strip() for attribute in source_attributes):
            raise ValueError("Source attribute names cannot be empty.")

        if len(source_attributes) != len(set(source_attributes)):
            raise ValueError("Source attributes must be unique.")

        object.__setattr__(self, "source_attributes", source_attributes)
        object.__setattr__(self, "variants", tuple(self.variants))
        object.__setattr__(self, "child_points", tuple(self.child_points))
        object.__setattr__(self, "metadata", dict(self.metadata))

        self._validate_unique_names(
            [variant.name for variant in self.variants],
            "variant",
        )

        self._validate_unique_names(
            [point.name for point in self.child_points],
            "child variation point",
        )

        for variant in self.variants:
            if (
                self.total_observations > 0
                and variant.occurrences > self.total_observations
            ):
                raise ValueError(
                    f"Occurrences of variant '{variant.name}' cannot exceed "
                    f"observations of variation point '{self.name}'."
                )

        try:
            object.__setattr__(
                self,
                "category",
                VariabilityCategory(self.category),
            )
        except ValueError as error:
            raise ValueError(
                f"Invalid variability category: {self.category!r}. "
                f"Expected one of: "
                f"{', '.join(category.value for category in VariabilityCategory)}."
            ) from error

    @staticmethod
    def _validate_unique_names(names: list[str], item_type: str) -> None:
        """Ensures sibling elements have unique names."""
        if len(names) != len(set(names)):
            raise ValueError(
                f"Duplicate {item_type} names are not allowed: {names}"
            )

    def iter_variation_points(self) -> Iterator[VariationPointSpec]:
        """Iterates recursively over this point and all subordinate points.

        Traversal includes both direct child points and points nested
        inside variants.
        """
        yield self

        for child_point in self.child_points:
            yield from child_point.iter_variation_points()

        for variant in self.variants:
            for child_point in variant.child_points:
                yield from child_point.iter_variation_points()


@dataclass(frozen=True, slots=True)
class VariabilitySpecification:
    """Complete variability specification for an expansion.

    This is the main output of phase 2 and the input expected by
    subsequent feature-model construction processes.
    """

    expansion_code: str
    expansion_name: str
    total_cards: int
    variation_points: tuple[VariationPointSpec, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.expansion_code or not self.expansion_code.strip():
            raise ValueError("Expansion code cannot be empty.")

        if not self.expansion_name or not self.expansion_name.strip():
            raise ValueError("Expansion name cannot be empty.")

        if self.total_cards < 0:
            raise ValueError("Total cards cannot be negative.")

        object.__setattr__(
            self,
            "variation_points",
            tuple(self.variation_points),
        )
        object.__setattr__(self, "metadata", dict(self.metadata))

        names = [point.name for point in self.variation_points]

        if len(names) != len(set(names)):
            raise ValueError(
                "Top-level variation point names must be unique."
            )

    def iter_variation_points(self) -> Iterator[VariationPointSpec]:
        """Iterates over all variation points in the specification."""
        for point in self.variation_points:
            yield from point.iter_variation_points()
