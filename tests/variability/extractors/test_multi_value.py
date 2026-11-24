
import pytest

from mtg_variability.variability.extractors.multi_value import MultiValueExtractor
from mtg_variability.variability.models import VariabilityCategory


def test_extracts_independent_values():
    extractor = MultiValueExtractor("colors")

    records = [
        {"name": "Card A", "colors": "['W', 'U']"},
        {"name": "Card B", "colors": "['W']"},
        {"name": "Card C", "colors": "['B', 'R']"},
        {"name": "Card D", "colors": "[]"},
    ]

    result = extractor.extract(records)

    assert len(result) == 1

    point = result[0]

    assert point.name == "colors"
    assert point.total_observations == 4
    assert point.missing_observations == 0

    variants = {variant.name: variant for variant in point.variants}

    assert set(variants) == {"B", "R", "U", "W"}
    assert variants["W"].occurrences == 2
    assert variants["U"].occurrences == 1
    assert variants["B"].occurrences == 1
    assert variants["R"].occurrences == 1


def test_empty_lists_are_valid_observations():
    extractor = MultiValueExtractor("colors")

    records = [
        {"name": "Card A", "colors": "['W']"},
        {"name": "Card B", "colors": "[]"},
        {"name": "Card C", "colors": "['U']"},
    ]

    result = extractor.extract(records)

    assert result[0].total_observations == 3
    assert result[0].missing_observations == 0


def test_missing_values_are_counted():
    extractor = MultiValueExtractor("colors")

    records = [
        {"name": "Card A", "colors": "['W']"},
        {"name": "Card B", "colors": ""},
        {"name": "Card C", "colors": "['U']"},
    ]

    result = extractor.extract(records)

    assert result[0].missing_observations == 1


def test_duplicate_values_are_counted_once_per_record():
    extractor = MultiValueExtractor("colors")

    records = [
        {"name": "Card A", "colors": "['W', 'W', 'U']"},
        {"name": "Card B", "colors": "['W']"},
    ]

    result = extractor.extract(records)

    variants = {variant.name: variant for variant in result[0].variants}

    assert variants["W"].occurrences == 2
    assert variants["U"].occurrences == 1


def test_preserves_examples():
    extractor = MultiValueExtractor("colors", max_examples=2)

    records = [
        {"name": "Card A", "colors": "['W', 'U']"},
        {"name": "Card B", "colors": "['W']"},
        {"name": "Card C", "colors": "['W']"},
    ]

    result = extractor.extract(records)

    variants = {variant.name: variant for variant in result[0].variants}

    assert variants["W"].examples == ("Card A", "Card B")
    assert variants["U"].examples == ("Card A",)


def test_does_not_extract_constant_attribute():
    extractor = MultiValueExtractor("colors")

    records = [
        {"name": "Card A", "colors": "['W']"},
        {"name": "Card B", "colors": "['W']"},
        {"name": "Card C", "colors": "[]"},
    ]

    assert extractor.extract(records) == ()


@pytest.mark.parametrize(
    ("category", "expected"),
    [
        ("functional", VariabilityCategory.FUNCTIONAL),
        ("collection", VariabilityCategory.COLLECTION),
        ("presentation", VariabilityCategory.PRESENTATION),
    ],
)
def test_assigns_category(category, expected):
    extractor = MultiValueExtractor("colors", category=category)

    records = [
        {"name": "Card A", "colors": "['W']"},
        {"name": "Card B", "colors": "['U']"},
    ]

    result = extractor.extract(records)

    assert result[0].category is expected


@pytest.mark.parametrize(
    "raw_value",
    [
        "W,U",
        "{'W', 'U'}",
        "not a list",
        "['W', 2]",
    ],
)
def test_rejects_invalid_serialized_lists(raw_value):
    extractor = MultiValueExtractor("colors")

    records = [
        {"name": "Card A", "colors": raw_value},
        {"name": "Card B", "colors": "['U']"},
    ]

    with pytest.raises(ValueError):
        extractor.extract(records)
