
"""Domain models for variability analysis.

These models represent the variability discovered in an expansion,
independently of any feature-modeling framework.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class VariabilityCategory(StrEnum):
    """Categories of variability represented in a specification."""

    FUNCTIONAL = "functional"
    COLLECTION = "collection"
    PRESENTATION = "presentation"


@dataclass(frozen=True, slots=True)
class VariationStatistics:
    """Aggregated statistics describing a variation point.

    Statistics are optional because not every variation point has
    meaningful numeric or cardinality information.
    """

    numeric_minimum: int | float | None = None
    numeric_maximum: int | float | None = None
    special_values: tuple[str, ...] = ()
    minimum_cardinality: int | None = None
    maximum_cardinality: int | None = None

    def __post_init__(self) -> None:
        """Validate and normalize statistical information."""
        if (
            self.numeric_minimum is not None
            and self.numeric_maximum is not None
            and self.numeric_minimum > self.numeric_maximum
        ):
            raise ValueError("Numeric minimum cannot exceed maximum.")

        if (
            self.minimum_cardinality is not None
            and self.minimum_cardinality < 0
        ):
            raise ValueError("Minimum cardinality cannot be negative.")

        if (
            self.maximum_cardinality is not None
            and self.maximum_cardinality < 0
        ):
            raise ValueError("Maximum cardinality cannot be negative.")

        if (
            self.minimum_cardinality is not None
            and self.maximum_cardinality is not None
            and self.minimum_cardinality > self.maximum_cardinality
        ):
            raise ValueError(
                "Minimum cardinality cannot exceed maximum cardinality."
            )

        special_values = tuple(self.special_values)

        if any(not value.strip() for value in special_values):
            raise ValueError("Special values cannot be empty.")

        if len(special_values) != len(set(special_values)):
            raise ValueError("Special values must be unique.")

        object.__setattr__(self, "special_values", special_values)


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
    """

    name: str
    source_attributes: tuple[str, ...] = ()
    variants: tuple[VariantSpec, ...] = ()
    child_points: tuple[VariationPointSpec, ...] = ()
    total_observations: int = 0
    missing_observations: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)
    category: VariabilityCategory = VariabilityCategory.FUNCTIONAL
    statistics: VariationStatistics = field(
        default_factory=VariationStatistics
    )

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

        if not isinstance(self.statistics, VariationStatistics):
            raise TypeError(
                "statistics must be an instance of VariationStatistics."
            )

    @staticmethod
    def _validate_unique_names(names: list[str], item_type: str) -> None:
        """Ensure sibling elements have unique names."""
        if len(names) != len(set(names)):
            raise ValueError(
                f"Duplicate {item_type} names are not allowed: {names}"
            )

    def iter_variation_points(self) -> Iterator[VariationPointSpec]:
        """Iterate recursively over this point and all subordinate points.

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
        """Iterate over all variation points in the specification."""
        for point in self.variation_points:
            yield from point.iter_variation_points()
