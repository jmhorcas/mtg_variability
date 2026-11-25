
"""Tests for the mana cost variation extractor."""

import pytest

from mtg_variability.variability.extractors.mana_cost import ManaCostExtractor


@pytest.fixture
def extractor() -> ManaCostExtractor:
    return ManaCostExtractor()


def _find_point(points, name):
    return next(point for point in points if point.name == name)


def _find_child(root, name):
    return next(point for point in root.child_points if point.name == name)


def _find_variant(point, name):
    return next(variant for variant in point.variants if variant.name == name)


def _extract_root(extractor, records):
    return _find_point(extractor.extract(records), "mana_cost")


class TestManaCostExtractor:
    def test_name(self, extractor):
        assert extractor.name == "mana-cost:manaCost"

    def test_empty_dataset(self, extractor):
        assert extractor.extract([]) == ()

    def test_extracts_mana_cost_hierarchy(self, extractor):
        records = [
            {"name": "Card A", "manaCost": "{2}{R}{B}"},
            {"name": "Card B", "manaCost": "{W}{U}"},
        ]

        points = extractor.extract(records)

        assert len(points) == 1
        assert points[0].name == "mana_cost"
        assert points[0].source_attributes == ("manaCost",)

    def test_extracts_generic_mana(self, extractor):
        records = [
            {"name": "Card A", "manaCost": "{2}{R}"},
            {"name": "Card B", "manaCost": "{3}{R}"},
            {"name": "Card C", "manaCost": "{R}"},
        ]

        root = _extract_root(extractor, records)
        point = _find_child(root, "generic")

        assert _find_variant(point, "0").occurrences == 1
        assert _find_variant(point, "2").occurrences == 1
        assert _find_variant(point, "3").occurrences == 1

    def test_sums_numeric_generic_symbols(self, extractor):
        records = [
            {"name": "Card A", "manaCost": "{2}{3}{R}"},
            {"name": "Card B", "manaCost": "{6}{R}"},
        ]

        root = _extract_root(extractor, records)
        point = _find_child(root, "generic")

        assert len(point.variants) == 2
        assert point.variants[0].name == "5"
        assert point.variants[0].occurrences == 1

    def test_extracts_all_five_colors(self, extractor):
        records = [
            {"name": "Card A", "manaCost": "{W}{U}{B}{R}{G}"},
            {"name": "Card B", "manaCost": "{W}{U}{B}{R}"},
        ]

        root = _extract_root(extractor, records)

        green = _find_child(root, "green")

        assert _find_variant(green, "0").occurrences == 1
        assert _find_variant(green, "1").occurrences == 1

        for color in ("white", "blue", "black", "red"):
            assert color not in {point.name for point in root.child_points}

    def test_extracts_colorless_mana(self, extractor):
        records = [
            {"name": "Card A", "manaCost": "{C}{C}"},
            {"name": "Card B", "manaCost": "{C}"},
        ]

        root = _extract_root(extractor, records)
        point = _find_child(root, "colorless")

        assert _find_variant(point, "1").occurrences == 1
        assert _find_variant(point, "2").occurrences == 1

    def test_does_not_confuse_colorless_with_generic(self, extractor):
        records = [
            {"name": "Card A", "manaCost": "{C}"},
            {"name": "Card B", "manaCost": "{1}"},
        ]

        root = _extract_root(extractor, records)

        colorless = _find_child(root, "colorless")
        generic = _find_child(root, "generic")

        assert _find_variant(colorless, "1").occurrences == 1
        assert _find_variant(colorless, "0").occurrences == 1

        assert _find_variant(generic, "0").occurrences == 1
        assert _find_variant(generic, "1").occurrences == 1

    def test_extracts_snow_mana(self, extractor):
        records = [
            {"name": "Card A", "manaCost": "{S}{S}"},
            {"name": "Card B", "manaCost": "{S}"},
        ]

        root = _extract_root(extractor, records)
        point = _find_child(root, "snow")

        assert _find_variant(point, "1").occurrences == 1
        assert _find_variant(point, "2").occurrences == 1

    @pytest.mark.parametrize("symbol", ["X", "Y", "Z"])
    def test_extracts_variable_symbols(self, extractor, symbol):
        records = [
            {"name": "Card A", "manaCost": f"{{{symbol}}}"},
            {"name": "Card B", "manaCost": ""},
        ]

        root = _extract_root(extractor, records)
        point = _find_child(root, "variable")

        assert _find_variant(point, "1").occurrences == 1
        assert _find_variant(point, "0").occurrences == 1

        symbol_point = _find_child(root, f"variable_symbol:{symbol}")
        assert _find_variant(symbol_point, "1").occurrences == 1
        assert _find_variant(symbol_point, "0").occurrences == 1

    @pytest.mark.parametrize(
        "symbol",
        ["W/U", "U/B", "B/R", "R/G", "G/W", "2/W", "2/U"],
    )
    def test_extracts_hybrid_symbols(self, extractor, symbol):
        records = [
            {"name": "Card A", "manaCost": f"{{{symbol}}}"},
            {"name": "Card B", "manaCost": ""},
        ]

        root = _extract_root(extractor, records)

        hybrid = _find_child(root, "hybrid")
        assert _find_variant(hybrid, "1").occurrences == 1
        assert _find_variant(hybrid, "0").occurrences == 1

        specific = _find_child(root, f"hybrid_symbol:{symbol}")
        assert _find_variant(specific, "1").occurrences == 1

    def test_hybrid_symbols_do_not_increment_individual_colors(self, extractor):
        records = [
            {"name": "Card A", "manaCost": "{W/U}"},
            {"name": "Card B", "manaCost": ""},
        ]

        root = _extract_root(extractor, records)

        hybrid = _find_child(root, "hybrid")

        child_names = {point.name for point in root.child_points}

        assert "hybrid" in child_names
        assert "white" not in child_names
        assert "blue" not in child_names

    @pytest.mark.parametrize(
        "symbol",
        ["W/P", "U/P", "B/P", "R/P", "G/P"],
    )
    def test_extracts_phyrexian_symbols(self, extractor, symbol):
        records = [
            {"name": "Card A", "manaCost": f"{{{symbol}}}"},
            {"name": "Card B", "manaCost": ""},
        ]

        root = _extract_root(extractor, records)

        phyrexian = _find_child(root, "phyrexian")
        assert _find_variant(phyrexian, "1").occurrences == 1
        assert _find_variant(phyrexian, "0").occurrences == 1

        specific = _find_child(root, f"phyrexian_symbol:{symbol}")
        assert _find_variant(specific, "1").occurrences == 1

    def test_extracts_hybrid_phyrexian_symbols(self, extractor):
        records = [
            {"name": "Card A", "manaCost": "{R/W/P}"},
            {"name": "Card B", "manaCost": ""},
        ]

        root = _extract_root(extractor, records)

        hybrid_phyrexian = _find_child(root, "hybrid_phyrexian")
        assert _find_variant(hybrid_phyrexian, "1").occurrences == 1
        assert _find_variant(hybrid_phyrexian, "0").occurrences == 1

        specific = _find_child(root, "hybrid_phyrexian_symbol:R/W/P")
        assert _find_variant(specific, "1").occurrences == 1

    def test_extracts_phyrexian_hybrid_combinations(self, extractor):
        records = [
            {"name": "Card A", "manaCost": "{W/P}{R/W/P}"},
            {"name": "Card B", "manaCost": ""},
        ]

        root = _extract_root(extractor, records)

        assert _find_variant(
            _find_child(root, "phyrexian"),
            "1",
        ).occurrences == 1

        assert _find_variant(
            _find_child(root, "hybrid_phyrexian"),
            "1",
        ).occurrences == 1

    def test_extracts_special_phyrexian_symbol_h(self, extractor):
        records = [
            {"name": "Card A", "manaCost": "{H}"},
            {"name": "Card B", "manaCost": ""},
        ]

        root = _extract_root(extractor, records)

        special = _find_child(root, "special")
        specific = _find_child(root, "special_symbol:H")

        assert _find_variant(special, "1").occurrences == 1
        assert _find_variant(special, "0").occurrences == 1
        assert _find_variant(specific, "1").occurrences == 1

    def test_preserves_exact_hybrid_combinations(self, extractor):
        records = [
            {"name": "Card A", "manaCost": "{W/U}"},
            {"name": "Card B", "manaCost": "{U/B}"},
        ]

        root = _extract_root(extractor, records)

        wu = _find_child(root, "hybrid_symbol:W/U")
        ub = _find_child(root, "hybrid_symbol:U/B")

        assert _find_variant(wu, "1").occurrences == 1
        assert _find_variant(wu, "0").occurrences == 1
        assert _find_variant(ub, "1").occurrences == 1
        assert _find_variant(ub, "0").occurrences == 1

    def test_counts_repeated_symbols(self, extractor):
        records = [
            {"name": "Card A", "manaCost": "{R}{R}{R}"},
            {"name": "Card B", "manaCost": "{R}"},
        ]

        root = _extract_root(extractor, records)
        point = _find_child(root, "red")

        assert _find_variant(point, "1").occurrences == 1
        assert _find_variant(point, "3").occurrences == 1

    def test_empty_mana_cost_is_valid_zero_cost(self, extractor):
        records = [
            {"name": "Card A", "manaCost": ""},
            {"name": "Card B", "manaCost": "{R}"},
        ]

        root = _extract_root(extractor, records)
        red = _find_child(root, "red")

        assert _find_variant(red, "0").occurrences == 1
        assert _find_variant(red, "1").occurrences == 1

    def test_whitespace_mana_cost_is_valid_zero_cost(self, extractor):
        records = [
            {"name": "Card A", "manaCost": "   "},
            {"name": "Card B", "manaCost": "{R}"},
        ]

        root = _extract_root(extractor, records)
        red = _find_child(root, "red")

        assert _find_variant(red, "0").occurrences == 1
        assert _find_variant(red, "1").occurrences == 1

    def test_missing_mana_cost_is_counted(self, extractor):
        records = [
            {"name": "Card A", "manaCost": "{R}"},
            {"name": "Card B", "manaCost": None},
            {"name": "Card C"},
        ]

        root = _extract_root(extractor, records)

        assert root.total_observations == 3
        assert root.missing_observations == 2
        assert root.child_points == ()

    def test_missing_cost_is_not_treated_as_zero_cost(self, extractor):
        records = [
            {"name": "Card A", "manaCost": "{R}"},
            {"name": "Card B", "manaCost": None},
        ]

        root = _extract_root(extractor, records)

        assert root.total_observations == 2
        assert root.missing_observations == 1
        assert root.child_points == ()

    def test_unknown_symbol_is_preserved(self, extractor):
        records = [
            {"name": "Card A", "manaCost": "{Q}"},
            {"name": "Card B", "manaCost": ""},
        ]

        root = _extract_root(extractor, records)

        other = _find_child(root, "other")
        specific = _find_child(root, "other_symbol:Q")

        assert _find_variant(other, "1").occurrences == 1
        assert _find_variant(specific, "1").occurrences == 1

    def test_malformed_text_is_not_silently_discarded(self, extractor):
        records = [
            {"name": "Card A", "manaCost": "{R"},
            {"name": "Card B", "manaCost": ""},
        ]

        root = _extract_root(extractor, records)

        other = _find_child(root, "other")
        assert _find_variant(other, "1").occurrences == 1

    def test_variant_examples_are_collected(self, extractor):
        records = [
            {"name": "Card A", "manaCost": "{R}"},
            {"name": "Card B", "manaCost": "{R}"},
            {"name": "Card C", "manaCost": "{U}"},
        ]

        root = _extract_root(extractor, records)
        red = _find_child(root, "red")

        assert _find_variant(red, "1").examples == ("Card A", "Card B")
        assert _find_variant(red, "0").examples == ("Card C",)

    def test_examples_are_unique(self, extractor):
        records = [
            {"name": "Card A", "manaCost": "{R}"},
            {"name": "Card A", "manaCost": "{R}"},
            {"name": "Card B", "manaCost": "{U}"},
        ]

        root = _extract_root(extractor, records)
        red = _find_child(root, "red")

        assert _find_variant(red, "1").examples == ("Card A",)

    def test_max_examples_is_respected(self):
        extractor = ManaCostExtractor(max_examples=2)
        records = [
            {"name": "Card A", "manaCost": "{R}"},
            {"name": "Card B", "manaCost": "{R}"},
            {"name": "Card C", "manaCost": "{R}"},
            {"name": "Card D", "manaCost": "{U}"},
        ]

        root = _extract_root(extractor, records)
        red = _find_child(root, "red")

        assert _find_variant(red, "1").examples == ("Card A", "Card B")

    def test_zero_max_examples(self):
        extractor = ManaCostExtractor(max_examples=0)
        records = [
            {"name": "Card A", "manaCost": "{R}"},
            {"name": "Card B", "manaCost": "{U}"},
        ]

        root = _extract_root(extractor, records)

        assert all(
            variant.examples == ()
            for point in root.child_points
            for variant in point.variants
        )

    def test_missing_example_attribute(self, extractor):
        records = [
            {"manaCost": "{R}"},
            {"manaCost": "{U}"},
        ]

        root = _extract_root(extractor, records)

        assert all(
            variant.examples == ()
            for point in root.child_points
            for variant in point.variants
        )

    def test_custom_attribute_names(self):
        extractor = ManaCostExtractor(
            attribute="cost",
            example_attribute="card_name",
        )
        records = [
            {"card_name": "Card A", "cost": "{R}"},
            {"card_name": "Card B", "cost": "{U}"},
        ]

        root = _extract_root(extractor, records)

        assert root.source_attributes == ("cost",)
        assert _find_variant(
            _find_child(root, "red"),
            "1",
        ).examples == ("Card A",)

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"attribute": ""},
            {"example_attribute": ""},
            {"max_examples": -1},
        ],
    )
    def test_invalid_configuration(self, kwargs):
        with pytest.raises(ValueError):
            ManaCostExtractor(**kwargs)

    def test_generic_dimension_calculates_numeric_bounds(self, extractor):
        records = [
            {"name": "Card A", "manaCost": "{1}{R}"},
            {"name": "Card B", "manaCost": "{2}{R}"},
            {"name": "Card C", "manaCost": "{3}{R}"},
            {"name": "Card D", "manaCost": "{5}{R}"},
        ]

        root = _extract_root(extractor, records)
        generic = _find_child(root, "generic")

        assert generic.statistics.numeric_minimum == 1
        assert generic.statistics.numeric_maximum == 5

    def test_generic_dimension_includes_zero_in_numeric_bounds(
        self,
        extractor,
    ):
        records = [
            {"name": "Card A", "manaCost": "{R}"},
            {"name": "Card B", "manaCost": "{R}"},
            {"name": "Card C", "manaCost": "{2}{R}"},
            {"name": "Card D", "manaCost": "{3}{R}"},
        ]

        root = _extract_root(extractor, records)
        generic = _find_child(root, "generic")

        assert generic.statistics.numeric_minimum == 0
        assert generic.statistics.numeric_maximum == 3

        variants = {
            variant.name: variant.occurrences
            for variant in generic.variants
        }

        assert variants == {
            "0": 2,
            "2": 1,
            "3": 1,
        }