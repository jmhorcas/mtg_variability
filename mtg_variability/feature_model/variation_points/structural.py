
"""Structural variation-point feature model builder."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from flamapy.metamodels.fm_metamodel.models.feature_model import (
    Feature,
    FeatureModel,
    Relation,
)

from mtg_variability.feature_model.variation_points.base import (
    VariationPoint,
    VariationPointBuilder,
    validate_feature_name,
)


class StructuralVariationPointBuilder(VariationPointBuilder):
    """Build hierarchical feature models from structural variation points."""

    def __init__(
        self,
        child_builders: Sequence[VariationPointBuilder] = (),
    ) -> None:
        self._child_builders = list(child_builders)

    def register_builder(self, builder: VariationPointBuilder) -> None:
        """Register a builder for nested variation points."""
        if builder not in self._child_builders:
            self._child_builders.append(builder)

    def supports(self, variation_point: VariationPoint) -> bool:
        """Check whether the variation point is a generic structural point."""
        name = str(variation_point.get("name", "")).strip().casefold()

        return name != "type" and bool(variation_point.get("child_points"))

    def build(self, variation_point: VariationPoint) -> FeatureModel:
        """Build a structural feature model recursively."""
        child_points = variation_point.get("child_points")

        if not isinstance(child_points, list) or not child_points:
            raise ValueError(
                f"Structural variation point "
                f"'{variation_point.get('name')}' must contain child points."
            )

        if variation_point.get("variants"):
            raise ValueError(
                f"Structural variation point "
                f"'{variation_point.get('name')}' cannot contain variants."
            )

        root = Feature(
            validate_feature_name(variation_point["name"]),
            is_abstract=True,
        )
        constraints = []

        for child_point in child_points:
            if not isinstance(child_point, Mapping):
                raise ValueError("Structural child points must be JSON objects.")

            child_model = self._build_child(child_point)
            child_root = child_model.root

            missing = self._validate_missing_observations(child_point)

            # A child is optional when it is absent in at least one
            # observation of its parent variation point.
            minimum = 0 if missing > 0 else 1

            root.add_relation(Relation(root, [child_root], minimum, 1))
            constraints.extend(self._get_constraints(child_model))

        return FeatureModel(root, constraints)

    def _build_child(
        self,
        child_point: VariationPoint,
    ) -> FeatureModel:
        """Select and execute exactly one builder for a child point."""
        matching = [
            builder
            for builder in self._child_builders
            if builder.supports(child_point)
        ]

        if len(matching) != 1:
            name = child_point.get("name", "<unnamed>")
            raise ValueError(
                f"Expected exactly one builder for structural child "
                f"'{name}', found {len(matching)}."
            )

        return matching[0].build(child_point)

    @staticmethod
    def _validate_missing_observations(
        variation_point: VariationPoint,
    ) -> int:
        """Validate and return the missing observation count."""
        missing = variation_point.get("missing_observations", 0)

        if (
            not isinstance(missing, int)
            or isinstance(missing, bool)
            or missing < 0
        ):
            raise ValueError(
                f"Invalid missing_observations in "
                f"'{variation_point.get('name')}'."
            )

        return missing

    @staticmethod
    def _get_constraints(model: FeatureModel) -> list:
        """Retrieve constraints from a feature model."""
        getter = getattr(model, "get_constraints", None)

        if callable(getter):
            return list(getter())

        for attribute in ("ctcs", "constraints"):
            constraints = getattr(model, attribute, None)

            if constraints is not None:
                return list(constraints)

        return []
