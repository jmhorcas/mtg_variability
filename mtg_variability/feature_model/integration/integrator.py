
"""Feature model integration utilities."""

from __future__ import annotations

from flamapy.metamodels.fm_metamodel.models.feature_model import (
    Feature,
    FeatureModel,
    Relation,
)


class FeatureModelIntegrator:
    """Replace template placeholders with generated feature models."""

    def integrate(
        self,
        template_model: FeatureModel,
        variation_model: FeatureModel,
        feature_name: str | None = None,
        missing_observations: int = 0,
    ) -> FeatureModel:
        """Replace a template feature with a generated variation model."""
        variation_root = variation_model.root
        target_name = feature_name or variation_root.name

        if variation_root.name != target_name:
            raise ValueError(
                f"Variation model root '{variation_root.name}' does not match "
                f"target '{target_name}'."
            )

        if (
            not isinstance(missing_observations, int)
            or isinstance(missing_observations, bool)
            or missing_observations < 0
        ):
            raise ValueError("missing_observations must be a non-negative integer.")

        placeholder = template_model.get_feature_by_name(target_name)

        if placeholder is None:
            raise ValueError(
                f"Template does not contain a feature named '{target_name}'."
            )

        if placeholder.name != variation_root.name:
            raise ValueError(
                f"Cannot replace '{placeholder.name}' with "
                f"'{variation_root.name}'."
            )

        if placeholder is template_model.root:
            variation_root.parent = None
            root = variation_root
        else:
            parent = placeholder.parent

            if parent is None:
                raise ValueError(
                    f"Feature '{target_name}' has no parent in the template."
                )

            relation = self._find_parent_relation(parent, placeholder)
            children = list(relation.children)
            children[children.index(placeholder)] = variation_root
            relation.children = children

            # Preserve the template's upper cardinality while deriving
            # mandatory/optional status from the observations.
            relation.card_min = 0 if missing_observations > 0 else 1

            variation_root.parent = parent
            placeholder.parent = None
            root = template_model.root

        constraints = [
            *self._get_constraints(template_model),
            *self._get_constraints(variation_model),
        ]

        return FeatureModel(root, constraints)

    @staticmethod
    def _find_parent_relation(
        parent: Feature,
        child: Feature,
    ) -> Relation:
        """Find the relation connecting a parent and child feature."""
        for relation in parent.get_relations():
            if child in relation.children:
                return relation

        raise ValueError(
            f"Could not find the relation containing '{child.name}' "
            f"under '{parent.name}'."
        )

    @staticmethod
    def _get_constraints(model: FeatureModel) -> list:
        """Retrieve the model's cross-tree constraints."""
        getter = getattr(model, "get_constraints", None)

        if callable(getter):
            return list(getter())

        for attribute in ("ctcs", "constraints"):
            constraints = getattr(model, attribute, None)

            if constraints is not None:
                return list(constraints)

        return []
