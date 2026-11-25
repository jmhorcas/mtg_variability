
"""Base abstractions for variation-point feature model builders."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from flamapy.metamodels.fm_metamodel.models.feature_model import FeatureModel


VariationPoint = Mapping[str, Any]


@runtime_checkable
class VariationPointBuilder(Protocol):
    """Protocol implemented by variation-point feature model builders."""

    def supports(self, variation_point: VariationPoint) -> bool:
        ...

    def build(self, variation_point: VariationPoint) -> FeatureModel:
        ...


def validate_feature_name(name: Any) -> str:
    """Validate and preserve a semantic feature name."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Feature names must be non-empty strings.")

    return name.strip()


def get_statistics(variation_point: VariationPoint) -> Mapping[str, Any]:
    """Return the variation point statistics."""
    statistics = variation_point.get("statistics")

    if not isinstance(statistics, Mapping):
        raise ValueError(
            f"Variation point '{variation_point.get('name')}' "
            "must contain a statistics mapping."
        )

    return statistics


def has_supported_statistics(variation_point: VariationPoint) -> bool:
    """Check whether the variation point has supported statistics."""
    statistics = variation_point.get("statistics")

    if not isinstance(statistics, Mapping):
        return False

    numeric = (
        statistics.get("numeric_minimum") is not None
        and statistics.get("numeric_maximum") is not None
    )
    cardinality = (
        statistics.get("minimum_cardinality") is not None
        or statistics.get("maximum_cardinality") is not None
    )
    special_values = bool(statistics.get("special_values"))

    return numeric or cardinality or special_values


def is_multivalue(variation_point: VariationPoint) -> bool:
    """Check whether the variation point represents a multivalue property."""
    statistics = variation_point.get("statistics")

    return (
        isinstance(statistics, Mapping)
        and (
            statistics.get("minimum_cardinality") is not None
            or statistics.get("maximum_cardinality") is not None
        )
    )


def is_numeric(variation_point: VariationPoint) -> bool:
    """Check whether the variation point represents a numeric property."""
    statistics = variation_point.get("statistics")

    return (
        isinstance(statistics, Mapping)
        and statistics.get("numeric_minimum") is not None
        and statistics.get("numeric_maximum") is not None
    )
