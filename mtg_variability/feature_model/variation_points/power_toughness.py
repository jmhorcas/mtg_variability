
"""Power and toughness variation-point feature model builder."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from flamapy.metamodels.fm_metamodel.models.feature_model import (
    Attribute,
    Feature,
    FeatureModel,
    FeatureType,
    Relation,
)

from mtg_variability.feature_model.variation_points.base import (
    VariationPoint,
    get_statistics,
    validate_feature_name,
)
from mtg_variability.feature_model.variation_points.numeric import (
    NumericVariationPointBuilder,
)


class PowerToughnessVariationPointBuilder:
    """Build the combined PowerToughness feature model."""

    PROPERTY_DOCUMENTATION = {
        "Power": "Amount of damage a creature deals in combat.",
        "Toughness": "Amount of damage a creature can sustain before dying.",
    }

    def build(
        self,
        variation_points: Mapping[str, VariationPoint],
    ) -> FeatureModel:
        """Build PowerToughness from its Power and Toughness specifications."""
        expected = {"Power", "Toughness"}

        if set(variation_points) != expected:
            raise ValueError(
                "PowerToughness requires exactly the Power and Toughness "
                "variation points."
            )

        root = Feature("PowerToughness", is_abstract=True)
        constraints = []

        for property_name in ("Power", "Toughness"):
            property_model = self._build_property(
                property_name,
                variation_points[property_name],
            )
            root.add_relation(
                Relation(root, [property_model.root], 1, 1)
            )
            constraints.extend(self._get_constraints(property_model))

        return FeatureModel(root, constraints)

    def _build_property(
        self,
        property_name: str,
        variation_point: VariationPoint,
    ) -> FeatureModel:
        """Build one numeric/special-valued property."""
        property_feature = Feature(property_name, is_abstract=True)
        property_feature.add_attribute(
            Attribute("gameplay", default_value=True)
        )
        property_feature.add_attribute(
            Attribute(
                "doc",
                default_value=self.PROPERTY_DOCUMENTATION[property_name],
            )
        )

        alternatives: list[Feature] = []
        constraints = []
        statistics = get_statistics(variation_point)

        numeric_minimum = statistics.get("numeric_minimum")
        numeric_maximum = statistics.get("numeric_maximum")

        if numeric_minimum is not None or numeric_maximum is not None:
            if numeric_minimum is None or numeric_maximum is None:
                raise ValueError(
                    f"Both numeric bounds are required for '{property_name}'."
                )

            numeric_specification = {
                "name": f"{property_name} value",
                "statistics": {
                    "numeric_minimum": numeric_minimum,
                    "numeric_maximum": numeric_maximum,
                },
            }

            numeric_model = NumericVariationPointBuilder().build(
                numeric_specification
            )
            alternatives.append(numeric_model.root)
            constraints.extend(self._get_constraints(numeric_model))

        special_values = statistics.get("special_values", [])

        if not isinstance(special_values, list):
            raise ValueError(
                f"Special values for '{property_name}' must be a list."
            )

        seen_special_values: set[str] = set()

        for value in special_values:
            if not isinstance(value, str) or not value:
                raise ValueError(
                    f"Invalid special value in '{property_name}'."
                )

            if value in seen_special_values:
                continue

            seen_special_values.add(value)
            label = "Star" if value == "*" else value
            special_feature = Feature(f"{property_name} {label}")
            special_feature.add_attribute(
                Attribute("value", default_value=value)
            )
            alternatives.append(special_feature)

        if not alternatives:
            raise ValueError(
                f"'{property_name}' has neither numeric bounds "
                "nor special values."
            )

        property_feature.add_relation(
            Relation(property_feature, alternatives, 1, 1)
        )

        return FeatureModel(property_feature, constraints)

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
