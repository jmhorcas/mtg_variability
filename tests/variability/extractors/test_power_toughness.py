
"""Tests for the power and toughness variation extractor."""

import pytest

from mtg_variability.variability.extractors.power_toughness import PowerToughnessExtractor


@pytest.fixture
def extractor() -> PowerToughnessExtractor:
    return PowerToughnessExtractor()


def _find_point(points, name):
    return next(point for point in points if point.name == name)


def _find_variant(point, name):
    return next(variant for variant in point.variants if variant.name == name)


class TestPowerToughnessExtractor:
    def test_name(self, extractor):
        assert extractor.name == "power-toughness"

    def test_empty_dataset(self, extractor):
        assert extractor.extract([]) == ()

    def test_extracts_power_and_toughness_independently(self, extractor):
        records = [
            {"name": "Card A", "power": "1", "toughness": "2"},
            {"name": "Card B", "power": "2", "toughness": "2"},
            {"name": "Card C", "power": "3", "toughness": "4"},
        ]

        points = extractor.extract(records)

        assert len(points) == 2
        assert {point.name for point in points} == {"power", "toughness"}

        power = _find_point(points, "power")
        toughness = _find_point(points, "toughness")

        assert {variant.name for variant in power.variants} == {"1", "2", "3"}
        assert {variant.name for variant in toughness.variants} == {"2", "4"}

    def test_power_occurrences(self, extractor):
        records = [
            {"name": "Card A", "power": "2", "toughness": "2"},
            {"name": "Card B", "power": "2", "toughness": "3"},
            {"name": "Card C", "power": "3", "toughness": "4"},
        ]

        point = _find_point(extractor.extract(records), "power")

        assert _find_variant(point, "2").occurrences == 2
        assert _find_variant(point, "3").occurrences == 1

    def test_toughness_occurrences(self, extractor):
        records = [
            {"name": "Card A", "power": "2", "toughness": "3"},
            {"name": "Card B", "power": "3", "toughness": "3"},
            {"name": "Card C", "power": "4", "toughness": "5"},
        ]

        point = _find_point(extractor.extract(records), "toughness")

        assert _find_variant(point, "3").occurrences == 2
        assert _find_variant(point, "5").occurrences == 1

    @pytest.mark.parametrize(
        "value",
        ["*", "X", "1+*", "*+1", "1+1", "∞"],
    )
    def test_preserves_symbolic_values(self, value):
        records = [
            {"name": "Card A", "power": value, "toughness": "2"},
            {"name": "Card B", "power": "2", "toughness": "3"},
        ]

        points = PowerToughnessExtractor().extract(records)
        power = _find_point(points, "power")

        assert value in {variant.name for variant in power.variants}

    def test_preserves_whitespace_normalization(self, extractor):
        records = [
            {"name": "Card A", "power": " 1 ", "toughness": "2"},
            {"name": "Card B", "power": "2", "toughness": "3"},
        ]

        point = _find_point(extractor.extract(records), "power")

        assert {variant.name for variant in point.variants} == {"1", "2"}

    def test_does_not_create_point_for_constant_power(self, extractor):
        records = [
            {"name": "Card A", "power": "2", "toughness": "2"},
            {"name": "Card B", "power": "2", "toughness": "3"},
        ]

        points = extractor.extract(records)

        assert "power" not in {point.name for point in points}
        assert "toughness" in {point.name for point in points}

    def test_does_not_create_point_for_constant_toughness(self, extractor):
        records = [
            {"name": "Card A", "power": "2", "toughness": "3"},
            {"name": "Card B", "power": "3", "toughness": "3"},
        ]

        points = extractor.extract(records)

        assert "power" in {point.name for point in points}
        assert "toughness" not in {point.name for point in points}

    def test_does_not_create_points_when_both_attributes_are_constant(
        self,
        extractor,
    ):
        records = [
            {"name": "Card A", "power": "2", "toughness": "3"},
            {"name": "Card B", "power": "2", "toughness": "3"},
        ]

        assert extractor.extract(records) == ()

    def test_missing_values_are_counted(self, extractor):
        records = [
            {"name": "Card A", "power": "2", "toughness": "3"},
            {"name": "Card B", "power": "", "toughness": "4"},
            {"name": "Card C", "power": "3", "toughness": ""},
            {"name": "Card D", "power": " ", "toughness": "5"},
        ]

        points = extractor.extract(records)

        power = _find_point(points, "power")
        toughness = _find_point(points, "toughness")

        assert power.total_observations == 4
        assert power.missing_observations == 2

        assert toughness.total_observations == 4
        assert toughness.missing_observations == 1

    def test_missing_values_do_not_contribute_to_variants(self, extractor):
        records = [
            {"name": "Card A", "power": "2", "toughness": "3"},
            {"name": "Card B", "power": "", "toughness": "4"},
            {"name": "Card C", "power": "3", "toughness": "5"},
        ]

        point = _find_point(extractor.extract(records), "power")

        assert {variant.name for variant in point.variants} == {"2", "3"}
        assert sum(variant.occurrences for variant in point.variants) == 2

    def test_variant_examples_are_collected(self, extractor):
        records = [
            {"name": "Card A", "power": "2", "toughness": "3"},
            {"name": "Card B", "power": "2", "toughness": "4"},
            {"name": "Card C", "power": "3", "toughness": "5"},
        ]

        point = _find_point(extractor.extract(records), "power")

        assert _find_variant(point, "2").examples == ("Card A", "Card B")
        assert _find_variant(point, "3").examples == ("Card C",)

    def test_examples_are_unique(self, extractor):
        records = [
            {"name": "Card A", "power": "2", "toughness": "3"},
            {"name": "Card A", "power": "2", "toughness": "4"},
            {"name": "Card B", "power": "3", "toughness": "5"},
        ]

        point = _find_point(extractor.extract(records), "power")

        assert _find_variant(point, "2").examples == ("Card A",)

    def test_max_examples_is_respected(self):
        extractor = PowerToughnessExtractor(max_examples=2)
        records = [
            {"name": "Card A", "power": "2", "toughness": "3"},
            {"name": "Card B", "power": "2", "toughness": "4"},
            {"name": "Card C", "power": "2", "toughness": "5"},
            {"name": "Card D", "power": "3", "toughness": "6"},
        ]

        point = _find_point(extractor.extract(records), "power")

        assert _find_variant(point, "2").examples == ("Card A", "Card B")

    def test_zero_max_examples(self):
        extractor = PowerToughnessExtractor(max_examples=0)
        records = [
            {"name": "Card A", "power": "2", "toughness": "3"},
            {"name": "Card B", "power": "3", "toughness": "4"},
        ]

        points = extractor.extract(records)

        assert all(
            variant.examples == ()
            for point in points
            for variant in point.variants
        )

    def test_missing_example_attribute(self, extractor):
        records = [
            {"power": "2", "toughness": "3"},
            {"power": "3", "toughness": "4"},
        ]

        points = extractor.extract(records)

        assert all(
            variant.examples == ()
            for point in points
            for variant in point.variants
        )

    def test_custom_attribute_names(self):
        extractor = PowerToughnessExtractor(
            power_attribute="strength",
            toughness_attribute="endurance",
            example_attribute="card_name",
        )
        records = [
            {"card_name": "Card A", "strength": "2", "endurance": "3"},
            {"card_name": "Card B", "strength": "3", "endurance": "4"},
        ]

        points = extractor.extract(records)

        assert {point.name for point in points} == {
            "strength",
            "endurance",
        }
        assert _find_variant(
            _find_point(points, "strength"),
            "2",
        ).examples == ("Card A",)

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"power_attribute": ""},
            {"toughness_attribute": ""},
            {"example_attribute": ""},
            {"power_attribute": "value", "toughness_attribute": "value"},
            {"max_examples": -1},
        ],
    )
    def test_invalid_configuration(self, kwargs):
        with pytest.raises(ValueError):
            PowerToughnessExtractor(**kwargs)

    def test_creates_point_for_constant_attribute_with_missing_values(
        self,
        extractor,
    ):
        records = [
            {"name": "Card A", "power": "2", "toughness": "3"},
            {"name": "Card B", "power": None, "toughness": "3"},
            {"name": "Card C", "power": "2", "toughness": "3"},
        ]

        points = extractor.extract(records)

        power = next(point for point in points if point.name == "power")

        assert len(power.variants) == 1
        assert power.variants[0].name == "2"
        assert power.variants[0].occurrences == 2
        assert power.missing_observations == 1
        assert power.statistics.numeric_minimum == 2
        assert power.statistics.numeric_maximum == 2