
import pytest

from mtg_variability.variability.extractors.categorical import CategoricalExtractor
from mtg_variability.variability.models import VariabilityCategory


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
def test_extractor_assigns_category(category, expected):
    extractor = CategoricalExtractor(
        "rarity",
        category=category,
    )

    records = [
        {"name": "Card A", "rarity": "common"},
        {"name": "Card B", "rarity": "rare"},
    ]

    result = extractor.extract(records)

    assert len(result) == 1
    assert result[0].category is expected


def test_extractor_defaults_to_functional_category():
    extractor = CategoricalExtractor("layout")

    records = [
        {"name": "Card A", "layout": "normal"},
        {"name": "Card B", "layout": "transform"},
    ]

    result = extractor.extract(records)

    assert result[0].category is VariabilityCategory.FUNCTIONAL


def test_extractor_rejects_invalid_category():
    with pytest.raises(ValueError, match="Invalid variability category"):
        CategoricalExtractor(
            "rarity",
            category="unknown",
        )
