
"""Attribute inspection utilities for variability analysis."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Mapping

from mtg_variability.variability.discovery.profiler import (
    AttributeProfile,
    DatasetProfile,
)


class AttributeClassification(Enum):
    """Statistical classification assigned to a dataset attribute."""

    EMPTY = "empty"
    CONSTANT = "constant"
    SPARSE = "sparse"
    CATEGORICAL = "categorical"
    NUMERIC = "numeric"
    HIGH_CARDINALITY = "high_cardinality"


@dataclass(frozen=True, slots=True)
class AttributeInspection:
    """Inspection result for a single dataset attribute."""

    profile: AttributeProfile
    classification: AttributeClassification
    is_candidate: bool
    requires_review: bool
    reasons: tuple[str, ...] = ()

    @property
    def name(self) -> str:
        """Returns the inspected attribute name."""
        return self.profile.name


@dataclass(frozen=True, slots=True)
class DatasetInspection:
    """Inspection results for all attributes in a dataset."""

    total_records: int
    attributes: Mapping[str, AttributeInspection]

    def __post_init__(self) -> None:
        if self.total_records < 0:
            raise ValueError("Total records cannot be negative.")

        attributes = dict(self.attributes)

        for name, inspection in attributes.items():
            if name != inspection.name:
                raise ValueError(
                    f"Attribute key '{name}' does not match "
                    f"inspection name '{inspection.name}'."
                )

            if inspection.profile.total_records != self.total_records:
                raise ValueError(
                    f"Attribute '{name}' has an inconsistent "
                    "number of records."
                )

        object.__setattr__(self, "attributes", attributes)

    @property
    def attribute_count(self) -> int:
        """Returns the number of inspected attributes."""
        return len(self.attributes)

    @property
    def candidates(self) -> tuple[AttributeInspection, ...]:
        """Returns attributes identified as variability candidates."""
        return tuple(
            inspection
            for inspection in self.attributes.values()
            if inspection.is_candidate
        )

    @property
    def attributes_requiring_review(
        self,
    ) -> tuple[AttributeInspection, ...]:
        """Returns attributes that require further inspection."""
        return tuple(
            inspection
            for inspection in self.attributes.values()
            if inspection.requires_review
        )


class DatasetInspector:
    """Classifies dataset attributes using configurable heuristics.

    The inspector is domain-independent. It identifies statistical
    characteristics that can help subsequent domain-specific extractors
    discover variation points.
    """

    def __init__(
        self,
        *,
        max_missing_ratio: float = 0.95,
        max_categorical_values: int = 100,
        high_cardinality_ratio: float = 0.90,
        min_records_for_ratio: int = 20,
    ) -> None:
        if not 0.0 <= max_missing_ratio <= 1.0:
            raise ValueError(
                "Maximum missing ratio must be between 0 and 1."
            )

        if max_categorical_values < 1:
            raise ValueError(
                "Maximum categorical values must be positive."
            )

        if not 0.0 <= high_cardinality_ratio <= 1.0:
            raise ValueError(
                "High cardinality ratio must be between 0 and 1."
            )

        if min_records_for_ratio < 1:
            raise ValueError(
                "Minimum records for ratio must be positive."
            )

        self.max_missing_ratio = max_missing_ratio
        self.max_categorical_values = max_categorical_values
        self.high_cardinality_ratio = high_cardinality_ratio
        self.min_records_for_ratio = min_records_for_ratio

    def inspect(self, profile: DatasetProfile) -> DatasetInspection:
        """Inspects all attributes in a dataset profile.

        Args:
            profile: Statistical profile produced by DatasetProfiler.

        Returns:
            Inspection results with attribute classifications.
        """
        inspections = {
            name: self._inspect_attribute(attribute)
            for name, attribute in profile.attributes.items()
        }

        return DatasetInspection(
            total_records=profile.total_records,
            attributes=inspections,
        )

    def _inspect_attribute(
        self,
        profile: AttributeProfile,
    ) -> AttributeInspection:
        """Classifies a single attribute."""
        if profile.non_missing_count == 0:
            return self._result(
                profile,
                AttributeClassification.EMPTY,
                is_candidate=False,
                requires_review=True,
                reason="The attribute contains no non-missing values.",
            )

        if profile.distinct_count == 1:
            return self._result(
                profile,
                AttributeClassification.CONSTANT,
                is_candidate=False,
                requires_review=False,
                reason="The attribute has only one distinct value.",
            )

        if profile.missing_ratio > self.max_missing_ratio:
            return self._result(
                profile,
                AttributeClassification.SPARSE,
                is_candidate=False,
                requires_review=True,
                reason=(
                    f"The missing ratio ({profile.missing_ratio:.2%}) "
                    "exceeds the configured threshold."
                ),
            )

        if self._is_numeric(profile):
            return self._result(
                profile,
                AttributeClassification.NUMERIC,
                is_candidate=True,
                requires_review=False,
                reason="All observed values are numeric.",
            )

        if self._is_high_cardinality(profile):
            return self._result(
                profile,
                AttributeClassification.HIGH_CARDINALITY,
                is_candidate=False,
                requires_review=True,
                reason=(
                    "The attribute has a high number or proportion "
                    "of distinct values."
                ),
            )

        return self._result(
            profile,
            AttributeClassification.CATEGORICAL,
            is_candidate=True,
            requires_review=False,
            reason="The attribute contains a manageable set of values.",
        )

    def _is_numeric(self, profile: AttributeProfile) -> bool:
        """Checks whether all observed values can be interpreted as numbers."""
        for value in profile.value_counts:
            try:
                number = Decimal(value.strip())
            except (InvalidOperation, ValueError):
                return False

            if not number.is_finite():
                return False

        return True

    def _is_high_cardinality(
        self,
        profile: AttributeProfile,
    ) -> bool:
        """Checks whether an attribute has excessive cardinality."""
        if profile.distinct_count > self.max_categorical_values:
            return True

        if profile.non_missing_count < self.min_records_for_ratio:
            return False

        distinct_ratio = (
            profile.distinct_count / profile.non_missing_count
        )

        return distinct_ratio >= self.high_cardinality_ratio

    @staticmethod
    def _result(
        profile: AttributeProfile,
        classification: AttributeClassification,
        *,
        is_candidate: bool,
        requires_review: bool,
        reason: str,
    ) -> AttributeInspection:
        """Builds a consistent attribute inspection result."""
        return AttributeInspection(
            profile=profile,
            classification=classification,
            is_candidate=is_candidate,
            requires_review=requires_review,
            reasons=(reason,),
        )
