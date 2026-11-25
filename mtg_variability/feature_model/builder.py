
"""Feature model builder for MTG variability specifications."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from flamapy.metamodels.fm_metamodel.models.feature_model import FeatureModel

from mtg_variability.feature_model.integration import FeatureModelIntegrator
from mtg_variability.feature_model.variation_points import (
    CategoricalVariationPointBuilder,
    MultivalueVariationPointBuilder,
    NumericVariationPointBuilder,
    PowerToughnessVariationPointBuilder,
    StructuralVariationPointBuilder,
    VariationPointBuilder,
    TypeVariationPointBuilder,
)


class FeatureModelBuilder:
    """Build feature models by integrating variation points into a template."""

    DEFAULT_FEATURE_NAMES = {
        "type": "Type",
        "supertypes": "Supertypes",
        "card_types": "Card Types",
        "layout": "Layout",
        "mana_cost": "Mana Cost",
        "mana_value": "Mana Value",
        "colors": "Colors",
        "color_identity": "Color Identity",
        "color_indicator": "Color Indicator",
        "power_toughness": "PowerToughness",
        "power": "Power",
        "toughness": "Toughness",
    }

    def __init__(
        self,
        template_model: FeatureModel,
        feature_names: Mapping[str, str] | None = None,
        variation_point_builders: Sequence[VariationPointBuilder] | None = None,
        integrator: FeatureModelIntegrator | None = None,
    ) -> None:
        self._template_model = template_model
        self._feature_names = {
            **self.DEFAULT_FEATURE_NAMES,
            **(feature_names or {}),
        }
        self._integrator = integrator or FeatureModelIntegrator()
        self._power_toughness_builder = PowerToughnessVariationPointBuilder()

        if variation_point_builders is None:
            self._variation_point_builders = self._create_default_builders()
        else:
            self._variation_point_builders = tuple(variation_point_builders)

    def build(self, specification: Mapping[str, Any]) -> FeatureModel:
        """Build a feature model from a Phase 2 specification."""
        variation_points = specification.get("variation_points")

        if not isinstance(variation_points, list):
            raise ValueError(
                "The specification must contain a 'variation_points' list."
            )

        feature_model = deepcopy(self._template_model)
        integrated_names: set[str] = set()

        for variation_point in variation_points:
            if not isinstance(variation_point, Mapping):
                raise ValueError("Variation points must be JSON objects.")

            source_name = self._get_name(variation_point)
            target_name = self._resolve_name(source_name)

            if target_name in integrated_names:
                raise ValueError(
                    f"More than one variation point maps to "
                    f"template feature '{target_name}'."
                )

            integrated_names.add(target_name)

            if self._is_power_toughness(source_name):
                variation_model = self._build_power_toughness(variation_point)
            else:
                prepared = self._prepare_point(
                    variation_point,
                    target_name,
                )
                variation_model = self._build_variation_point(prepared)

            missing = self._get_missing_observations(variation_point)

            feature_model = self._integrator.integrate(
                feature_model,
                variation_model,
                feature_name=target_name,
                missing_observations=missing,
            )

        return feature_model

    def _build_variation_point(
        self,
        variation_point: Mapping[str, Any],
    ) -> FeatureModel:
        """Select and execute the strategy for one variation point."""
        matching = [
            builder
            for builder in self._variation_point_builders
            if builder.supports(variation_point)
        ]

        if len(matching) != 1:
            name = variation_point.get("name", "<unnamed>")
            raise ValueError(
                f"Expected exactly one builder for '{name}', "
                f"found {len(matching)}."
            )

        return matching[0].build(variation_point)

    def _build_power_toughness(
        self,
        variation_point: Mapping[str, Any],
    ) -> FeatureModel:
        """Build the combined PowerToughness model."""
        child_points = variation_point.get("child_points")

        if not isinstance(child_points, list):
            raise ValueError(
                "PowerToughness must contain a 'child_points' list."
            )

        properties: dict[str, Mapping[str, Any]] = {}

        for child_point in child_points:
            if not isinstance(child_point, Mapping):
                raise ValueError(
                    "PowerToughness child points must be JSON objects."
                )

            source_name = self._get_name(child_point)
            property_name = self._resolve_name(source_name)

            if property_name in {"Power", "Toughness"}:
                properties[property_name] = self._prepare_point(
                    child_point,
                    property_name,
                )

        return self._power_toughness_builder.build(properties)

    def _prepare_point(
        self,
        variation_point: Mapping[str, Any],
        target_name: str,
    ) -> dict[str, Any]:
        """Copy a point and recursively resolve its semantic names."""
        prepared = deepcopy(dict(variation_point))
        prepared["name"] = target_name

        child_points = prepared.get("child_points")

        if isinstance(child_points, list):
            prepared["child_points"] = [
                self._prepare_child_point(child)
                for child in child_points
            ]

        return prepared

    def _prepare_child_point(self, child_point: Any) -> Any:
        """Prepare a nested point using the configured name mapping."""
        if not isinstance(child_point, Mapping):
            return child_point

        source_name = self._get_name(child_point)
        target_name = self._resolve_name(source_name)

        return self._prepare_point(child_point, target_name)

    def _resolve_name(self, source_name: str) -> str:
        """Resolve a source name to its exact semantic feature name."""
        return self._feature_names.get(source_name, source_name)

    @staticmethod
    def _get_name(variation_point: Mapping[str, Any]) -> str:
        """Return a validated variation-point name."""
        name = variation_point.get("name")

        if not isinstance(name, str) or not name.strip():
            raise ValueError("Variation points must have a non-empty name.")

        return name.strip()

    @staticmethod
    def _get_missing_observations(
        variation_point: Mapping[str, Any],
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
    def _is_power_toughness(source_name: str) -> bool:
        return source_name.strip().lower() in {
            "power_toughness",
            "powertoughness",
        }

    @staticmethod
    def _create_default_builders() -> tuple[VariationPointBuilder, ...]:
        """Create the default variation-point strategy set."""
        categorical = CategoricalVariationPointBuilder()
        multivalue = MultivalueVariationPointBuilder()
        numeric = NumericVariationPointBuilder()
        type_system = TypeVariationPointBuilder()

        structural = StructuralVariationPointBuilder(
            child_builders=(categorical, multivalue, numeric)
        )
        structural.register_builder(structural)

        return (
            type_system,
            structural,
            categorical,
            multivalue,
            numeric,
        )

