
"""Numeric variation-point feature model builder."""

from __future__ import annotations

from collections.abc import Mapping

from flamapy.core.models.ast import AST, ASTOperation, Node, NodeType
from flamapy.metamodels.fm_metamodel.models.feature_model import (
    Constraint,
    Feature,
    FeatureModel,
    FeatureType,
)

from mtg_variability.feature_model.variation_points.base import (
    VariationPoint,
    validate_feature_name,
    get_statistics,
)


class NumericVariationPointBuilder:
    """Build feature models for numeric variation points."""

    def supports(self, variation_point: VariationPoint) -> bool:
        """Return whether the variation point is numeric."""
        statistics = variation_point.get("statistics")

        return (
            not variation_point.get("child_points")
            and isinstance(statistics, Mapping)
            and statistics.get("numeric_minimum") is not None
            and statistics.get("numeric_maximum") is not None
        )

    def build(self, variation_point: VariationPoint) -> FeatureModel:
        """Build an independent feature model for a numeric property."""
        if variation_point.get("child_points"):
            raise ValueError(
                f"Numeric variation point "
                f"{variation_point.get('name')!r} cannot contain child points"
            )

        statistics = get_statistics(variation_point)

        minimum = statistics.get("numeric_minimum")
        maximum = statistics.get("numeric_maximum")

        feature_name = validate_feature_name(variation_point["name"])

        feature = Feature(
            feature_name,
            feature_type=FeatureType.INTEGER,
        )

        constraints = self._build_bounds(
            feature_name=feature_name,
            minimum=minimum,
            maximum=maximum,
        )

        return FeatureModel(feature, constraints)

    @staticmethod
    def _build_bounds(
        feature_name: str,
        minimum: object,
        maximum: object,
    ) -> list[Constraint]:
        """Build the lower and upper bound constraint for a feature."""
        if (
            isinstance(minimum, bool)
            or not isinstance(minimum, int)
            or isinstance(maximum, bool)
            or not isinstance(maximum, int)
            or minimum > maximum
        ):
            raise ValueError(
                f"Invalid numeric bounds for {feature_name!r}: "
                f"[{minimum!r}, {maximum!r}]"
            )

        lower_bound = AST.create_binary_operation(
            NumericVariationPointBuilder._ast_operation("GREATER_EQUALS"),
            Node(feature_name, node_type=NodeType.FEATURE),
            Node(minimum, node_type=NodeType.LITERAL),
        )

        upper_bound = AST.create_binary_operation(
            NumericVariationPointBuilder._ast_operation("LOWER_EQUALS"),
            Node(feature_name, node_type=NodeType.FEATURE),
            Node(maximum, node_type=NodeType.LITERAL),
        )

        bounds = AST.create_binary_operation(
            NumericVariationPointBuilder._ast_operation("AND"),
            lower_bound.root,
            upper_bound.root,
        )

        return [
            Constraint(
                f"{feature_name}_bounds",
                bounds,
            )
        ]

    @staticmethod
    def _ast_operation(*names: str) -> ASTOperation:
        """Resolve an AST operation using the available Flamapy enum names."""
        for name in names:
            operation = getattr(ASTOperation, name, None)
            if operation is not None:
                return operation

        raise ValueError(
            "None of the expected AST operations are available: "
            f"{', '.join(names)}"
        )
