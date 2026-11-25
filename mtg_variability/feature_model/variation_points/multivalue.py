
"""Multivalued variation-point feature model builder."""

from __future__ import annotations

from collections.abc import Mapping

from flamapy.metamodels.fm_metamodel.models.feature_model import (
    Feature,
    FeatureModel,
    Relation,
)

from mtg_variability.feature_model.variation_points.base import (
    VariationPoint,
    validate_feature_name,
    get_statistics,
)


class MultivalueVariationPointBuilder:
    """Build feature models for multivalued variation points."""

    def supports(self, variation_point: VariationPoint) -> bool:
        """Return whether the variation point is multivalued."""
        statistics = variation_point.get("statistics")

        return (
            not variation_point.get("child_points")
            and isinstance(statistics, Mapping)
            and (
                statistics.get("minimum_cardinality") is not None
                or statistics.get("maximum_cardinality") is not None
            )
        )

    def build(self, variation_point: VariationPoint) -> FeatureModel:
        """Build an independent feature model for a multivalued property."""
        if variation_point.get("child_points"):
            raise ValueError(
                f"Multivalued variation point "
                f"{variation_point.get('name')!r} cannot contain child points"
            )

        variants = variation_point.get("variants")

        if not isinstance(variants, list) or not variants:
            raise ValueError(
                f"Multivalued variation point "
                f"{variation_point.get('name')!r} has no variants"
            )

        statistics = get_statistics(variation_point)

        required_statistics = {
            "minimum_cardinality",
            "maximum_cardinality",
        }
        missing_statistics = required_statistics - statistics.keys()

        if missing_statistics:
            raise ValueError(
                f"Missing cardinality statistics for variation point "
                f"{variation_point['name']!r}: "
                f"{sorted(missing_statistics)}"
            )

        minimum = statistics["minimum_cardinality"]
        maximum = statistics["maximum_cardinality"]

        if (
            isinstance(minimum, bool)
            or not isinstance(minimum, int)
            or isinstance(maximum, bool)
            or not isinstance(maximum, int)
            or minimum < 0
            or maximum < minimum
            or maximum > len(variants)
        ):
            raise ValueError(
                f"Invalid cardinality bounds for variation point "
                f"{variation_point['name']!r}: "
                f"[{minimum}, {maximum}] with {len(variants)} variants"
            )

        root = Feature(validate_feature_name(variation_point["name"]))

        value_features: list[Feature] = []
        feature_names: set[str] = set()

        for variant in variants:
            if not isinstance(variant, Mapping):
                raise ValueError(
                    f"Invalid variant in variation point "
                    f"{variation_point['name']!r}"
                )

            variant_name = variant.get("name")

            if not isinstance(variant_name, str) or not variant_name.strip():
                raise ValueError(
                    f"Invalid variant name in variation point "
                    f"{variation_point['name']!r}: {variant_name!r}"
                )

            name = validate_feature_name(variant_name)

            if name in feature_names:
                raise ValueError(
                    f"Duplicate variant feature {name!r} in "
                    f"variation point {variation_point['name']!r}"
                )

            feature_names.add(name)
            value_features.append(Feature(name))

        root.add_relation(
            Relation(root, value_features, minimum, maximum)
        )

        return FeatureModel(root)
