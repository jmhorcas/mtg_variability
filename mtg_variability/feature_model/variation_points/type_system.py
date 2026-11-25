
"""MTG type-system feature model builder."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from flamapy.metamodels.fm_metamodel.models.feature_model import (
    Feature,
    FeatureModel,
    Relation,
)

from mtg_variability.feature_model.variation_points.base import (
    VariationPoint,
    VariationPointBuilder,
    get_statistics,
    validate_feature_name,
)


class TypeVariationPointBuilder(VariationPointBuilder):
    """Build the MTG type hierarchy, associating subtypes with card types."""

    SUPERTYPES_NAME = "Supertypes"
    CARD_TYPES_NAME = "Card Types"

    def supports(self, variation_point: VariationPoint) -> bool:
        """Check whether the variation point represents the MTG type system."""
        name = variation_point.get("name")
        return isinstance(name, str) and name.strip().lower() == "type"

    def build(self, variation_point: VariationPoint) -> FeatureModel:
        """Build the Type feature model from its hierarchical specification."""
        children = variation_point.get("child_points", [])

        points = {
            self._normalise_key(self._get_name(point)): point
            for point in children
        }

        supertypes = points.get("supertypes")
        card_types = points.get("card_types")
        subtypes = points.get("subtypes")

        if supertypes is None or card_types is None:
            raise ValueError(
                "Type requires both supertypes and card_types."
            )

        root = Feature("Type", is_abstract=True)

        supertypes_group = self._build_value_group(
            supertypes,
            "Supertypes",
        )
        root.add_relation(Relation(root, [supertypes_group], 0, 1))

        card_types_group, card_type_features = self._build_card_types(card_types)

        root.add_relation(Relation(root, [card_types_group], 1, 1))

        if subtypes is not None:
            self._attach_subtypes(card_type_features, subtypes)

        return FeatureModel(root)

    def _build_card_types(
        self,
        variation_point: Mapping[str, Any],
    ) -> tuple[Feature, dict[str, Feature]]:
        """Build the Card Types group and its selectable card types."""
        group = Feature(self.CARD_TYPES_NAME, is_abstract=True)
        variants = self._get_variants(variation_point)

        features: dict[str, Feature] = {}
        children: list[Feature] = []

        for variant in variants:
            name = validate_feature_name(variant.get("name"))
            key = name.casefold()

            if key in features:
                raise ValueError(f"Duplicate card type '{name}'.")

            feature = Feature(name)
            features[key] = feature
            children.append(feature)

        minimum, maximum = self._get_cardinality(variation_point)

        group.add_relation(
            Relation(group, children, minimum, maximum)
        )

        return group, features

    def _attach_subtypes(
        self,
        card_type_features: Mapping[str, Feature],
        subtypes_container: Mapping[str, Any],
    ) -> None:
        """Attach each subtype group to its corresponding card type."""
        subtype_points = subtypes_container.get("child_points")

        if not isinstance(subtype_points, list):
            raise ValueError(
                "The subtypes container must contain child_points."
            )

        for subtype_point in subtype_points:
            if not isinstance(subtype_point, Mapping):
                raise ValueError("Subtype points must be JSON objects.")

            source_name = self._get_name(subtype_point)

            if not source_name.startswith("subtypes:"):
                raise ValueError(
                    f"Unexpected subtype point name '{source_name}'."
                )

            card_type_name = source_name.split(":", maxsplit=1)[1].casefold()

            card_type = card_type_features.get(card_type_name)

            if card_type is None:
                raise ValueError(
                    f"Subtype group '{source_name}' has no corresponding "
                    f"card type in Card Types."
                )

            variants = self._get_variants(subtype_point)

            if not variants:
                continue

            group_name = f"{card_type.name} subtypes"
            group = Feature(group_name, is_abstract=True)

            subtype_features = [
                Feature(validate_feature_name(variant.get("name")))
                for variant in variants
            ]

            minimum, maximum = self._get_cardinality(subtype_point)

            group.add_relation(
                Relation(group, subtype_features, minimum, maximum)
            )

            missing = self._get_missing_observations(subtype_point)
            group_minimum = 0 if missing > 0 else 1

            card_type.add_relation(
                Relation(card_type, [group], group_minimum, 1)
            )

    def _build_value_group(
        self,
        variation_point: Mapping[str, Any],
        group_name: str,
    ) -> Feature:
        """Build a multivalued group such as Supertypes."""
        group = Feature(group_name, is_abstract=True)
        variants = self._get_variants(variation_point)

        children = [
            Feature(validate_feature_name(variant.get("name")))
            for variant in variants
        ]

        minimum, maximum = self._get_cardinality(variation_point)

        group.add_relation(
            Relation(group, children, minimum, maximum)
        )

        return group

    @staticmethod
    def _get_variants(
        variation_point: Mapping[str, Any],
    ) -> list[Mapping[str, Any]]:
        """Retrieve and validate variation point variants."""
        variants = variation_point.get("variants")

        if not isinstance(variants, list):
            raise ValueError(
                f"Variation point '{variation_point.get('name')}' "
                "must contain a variants list."
            )

        if not all(isinstance(variant, Mapping) for variant in variants):
            raise ValueError("All variants must be JSON objects.")

        return variants

    @staticmethod
    def _get_cardinality(
        variation_point: Mapping[str, Any],
    ) -> tuple[int, int]:
        """Return the minimum and maximum selection cardinalities."""
        statistics = get_statistics(variation_point)

        minimum = statistics.get("minimum_cardinality")
        maximum = statistics.get("maximum_cardinality")

        if (
            not isinstance(minimum, int)
            or isinstance(minimum, bool)
            or not isinstance(maximum, int)
            or isinstance(maximum, bool)
        ):
            raise ValueError(
                f"Missing cardinality statistics for "
                f"'{variation_point.get('name')}'."
            )

        if minimum < 0 or maximum < minimum:
            raise ValueError(
                f"Invalid cardinality [{minimum}..{maximum}] for "
                f"'{variation_point.get('name')}'."
            )

        if maximum > len(TypeVariationPointBuilder._get_variants(variation_point)):
            raise ValueError(
                f"Maximum cardinality exceeds the number of variants in "
                f"'{variation_point.get('name')}'."
            )

        return minimum, maximum

    @staticmethod
    def _get_missing_observations(
        variation_point: Mapping[str, Any],
    ) -> int:
        """Validate and return missing observations."""
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
    def _get_name(variation_point: Mapping[str, Any]) -> str:
        """Return a validated variation point name."""
        return validate_feature_name(variation_point.get("name"))

    @staticmethod
    def _normalise_key(name: str) -> str:
        """Normalize a semantic feature name for specification lookup."""
        return "_".join(name.strip().casefold().split())
