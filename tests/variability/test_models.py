import pytest

from mtg_variability.variability.models import (
    VariabilityCategory,
    VariationPointSpec,
)


@pytest.mark.parametrize(
    ("category", "expected"),
    [
        (VariabilityCategory.FUNCTIONAL, VariabilityCategory.FUNCTIONAL),
        (VariabilityCategory.COLLECTION, VariabilityCategory.COLLECTION),
        (VariabilityCategory.PRESENTATION, VariabilityCategory.PRESENTATION),
        ("functional", VariabilityCategory.FUNCTIONAL),
        ("collection", VariabilityCategory.COLLECTION),
        ("presentation", VariabilityCategory.PRESENTATION),
    ],
)
def test_variation_point_category(category, expected):
    point = VariationPointSpec(
        name="rarity",
        category=category,
    )

    assert point.category is expected


def test_variation_point_rejects_invalid_category():
    with pytest.raises(ValueError, match="Invalid variability category"):
        VariationPointSpec(
            name="rarity",
            category="unknown",
        )


def test_variation_point_defaults_to_functional_category():
    point = VariationPointSpec(name="power")

    assert point.category is VariabilityCategory.FUNCTIONAL