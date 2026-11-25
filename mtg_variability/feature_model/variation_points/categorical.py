
"""Categorical variation-point feature model builder."""

from __future__ import annotations

from collections.abc import Mapping

from flamapy.metamodels.fm_metamodel.models.feature_model import (
    Feature,
    FeatureModel,
    Relation,
)

from mtg_variability.feature_model.variation_points.base import (
    VariationPoint,
    VariationPointBuilder,
    has_supported_statistics,
    is_multivalue,
    is_numeric,
    validate_feature_name,
)


class CategoricalVariationPointBuilder(VariationPointBuilder):
    """Build feature models for categorical variation points."""

    def supports(self, variation_point: VariationPoint) -> bool:
        return (
            not variation_point.get("child_points")
            and not is_multivalue(variation_point)
            and not is_numeric(variation_point)
            and not has_supported_statistics(variation_point)
        )

    def build(self, variation_point: VariationPoint) -> FeatureModel:
        """Build a categorical feature model."""
        variants = variation_point.get("variants")

        if not isinstance(variants, list) or not variants:
            raise ValueError(
                f"Categorical variation point "
                f"'{variation_point.get('name')}' must contain variants."
            )

        root = Feature(validate_feature_name(variation_point["name"]))
        children: list[Feature] = []
        names: set[str] = set()

        for variant in variants:
            if not isinstance(variant, Mapping):
                raise ValueError("Categorical variants must be JSON objects.")

            name = validate_feature_name(variant.get("name"))

            if name in names:
                raise ValueError(
                    f"Duplicate categorical variant '{name}' in "
                    f"'{root.name}'."
                )

            names.add(name)
            children.append(Feature(name))

        root.add_relation(Relation(root, children, 1, 1))

        return FeatureModel(root)
