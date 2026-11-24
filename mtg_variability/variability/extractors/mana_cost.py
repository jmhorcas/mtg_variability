
"""Mana cost variation extraction."""

import re
from collections import Counter, defaultdict
from collections.abc import Sequence

from mtg_variability.variability.extractors.base import BaseVariationExtractor
from mtg_variability.variability.models import VariantSpec, VariationPointSpec
from mtg_variability.variability.protocols import CardRecord


class ManaCostExtractor(BaseVariationExtractor):
    """Extract mana cost variation from Magic: The Gathering cards.

    Each mana cost is decomposed into independent dimensions. Numeric generic
    costs are summed, while hybrid, Phyrexian and other special symbols are
    counted separately and retain their exact symbol representation.

    An empty mana cost is treated as a valid zero-cost value. A missing or
    null attribute is treated as missing data.
    """

    _SYMBOL_PATTERN = re.compile(r"\{([^{}]+)\}")
    _COLORED_SYMBOLS = {
        "W": "white",
        "U": "blue",
        "B": "black",
        "R": "red",
        "G": "green",
    }
    _VARIABLE_SYMBOLS = {"X", "Y", "Z"}

    _BASE_DIMENSIONS = (
        "generic",
        "white",
        "blue",
        "black",
        "red",
        "green",
        "colorless",
        "snow",
        "variable",
        "hybrid",
        "phyrexian",
        "hybrid_phyrexian",
        "special",
        "other",
    )

    def __init__(
        self,
        attribute: str = "manaCost",
        example_attribute: str = "name",
        max_examples: int = 3,
    ) -> None:
        if not attribute.strip():
            raise ValueError("attribute cannot be empty.")
        if not example_attribute.strip():
            raise ValueError("example_attribute cannot be empty.")
        if max_examples < 0:
            raise ValueError("max_examples cannot be negative.")

        self._attribute = attribute
        self._example_attribute = example_attribute
        self._max_examples = max_examples

    @property
    def name(self) -> str:
        """Return the extractor identifier."""
        return f"mana-cost:{self._attribute}"

    
    def _extract(
        self,
        records: Sequence[CardRecord],
    ) -> Sequence[VariationPointSpec]:
        parsed_records = []
        dimensions = set(self._BASE_DIMENSIONS)
        missing_count = 0

        # First pass: parse costs and discover every dimension.
        for record in records:
            raw_cost = record.get(self._attribute)

            if raw_cost is None:
                missing_count += 1
                continue

            cost = str(raw_cost).strip()
            components = self._parse_cost(cost)
            dimensions.update(components)

            example = self._get_normalized_value(
                record,
                self._example_attribute,
            )
            parsed_records.append((components, example))

        # No valid mana cost was available.
        if not parsed_records:
            return ()

        # Second pass: record every dimension for every valid cost.
        observations: dict[str, list[tuple[int, str]]] = {
            dimension: [] for dimension in dimensions
        }

        for components, example in parsed_records:
            for dimension in dimensions:
                value = components.get(dimension, 0)
                observations[dimension].append((value, example))

        child_points = []

        for dimension in sorted(dimensions):
            point = self._build_point(
                dimension,
                observations[dimension],
                len(records),
                missing_count,
            )

            if point is not None:
                child_points.append(point)

        # Preserve missing-data information even when no dimension varies.
        if not child_points and missing_count == 0:
            return ()

        root = VariationPointSpec(
            name="mana_cost",
            source_attributes=(self._attribute,),
            child_points=tuple(child_points),
            total_observations=len(records),
            missing_observations=missing_count,
        )

        return (root,)

    def _parse_cost(self, cost: str) -> Counter[str]:
        """Parse a mana cost into independently counted dimensions."""
        components: Counter[str] = Counter()

        matches = list(self._SYMBOL_PATTERN.finditer(cost))

        for match in matches:
            symbol = match.group(1).strip().upper()

            if not symbol:
                continue

            self._parse_symbol(symbol, components)

        # Preserve unexpected text instead of silently discarding it.
        remainder = self._SYMBOL_PATTERN.sub("", cost)
        remainder = remainder.strip()

        if remainder:
            components["other"] += 1
            components[f"other_symbol:{remainder}"] += 1

        return components

    def _parse_symbol(
        self,
        symbol: str,
        components: Counter[str],
    ) -> None:
        """Classify and count a single mana symbol."""
        if symbol.isdigit():
            components["generic"] += int(symbol)
            return

        if symbol in self._COLORED_SYMBOLS:
            components[self._COLORED_SYMBOLS[symbol]] += 1
            return

        if symbol == "C":
            components["colorless"] += 1
            return

        if symbol == "S":
            components["snow"] += 1
            return

        if symbol in self._VARIABLE_SYMBOLS:
            components["variable"] += 1
            components[f"variable_symbol:{symbol}"] += 1
            return

        if symbol == "H":
            components["special"] += 1
            components["special_symbol:H"] += 1
            return

        parts = symbol.split("/")

        if self._is_phyrexian_symbol(parts):
            if len(parts) == 2:
                components["phyrexian"] += 1
                components[f"phyrexian_symbol:{symbol}"] += 1
            else:
                components["hybrid_phyrexian"] += 1
                components[f"hybrid_phyrexian_symbol:{symbol}"] += 1
            return

        if self._is_hybrid_symbol(parts):
            components["hybrid"] += 1
            components[f"hybrid_symbol:{symbol}"] += 1
            return

        components["other"] += 1
        components[f"other_symbol:{symbol}"] += 1

    @classmethod
    def _is_phyrexian_symbol(cls, parts: list[str]) -> bool:
        """Return whether a symbol has a Phyrexian component."""
        if len(parts) not in (2, 3) or parts[-1] != "P":
            return False

        if len(parts) == 2:
            return parts[0] in cls._COLORED_SYMBOLS

        return (
            parts[0] in cls._COLORED_SYMBOLS
            and parts[1] in cls._COLORED_SYMBOLS
            and parts[0] != parts[1]
        )

    @classmethod
    def _is_hybrid_symbol(cls, parts: list[str]) -> bool:
        """Return whether a symbol represents a hybrid mana cost."""
        if len(parts) != 2:
            return False

        first, second = parts

        valid_first = first in cls._COLORED_SYMBOLS or first.isdigit()
        valid_second = second in cls._COLORED_SYMBOLS

        return valid_first and valid_second

    def _build_point(
        self,
        dimension: str,
        observations: list[tuple[int, str]],
        total_observations: int,
        missing_observations: int,
    ) -> VariationPointSpec | None:
        """Build a variation point from the observed component counts."""
        counts: Counter[int] = Counter()
        examples: dict[int, list[str]] = defaultdict(list)

        for value, example in observations:
            counts[value] += 1

            if (
                example
                and example not in examples[value]
                and len(examples[value]) < self._max_examples
            ):
                examples[value].append(example)

        # A constant component does not represent a variation point.
        if len(counts) < 2:
            return None

        variants = tuple(
            VariantSpec(
                name=str(value),
                occurrences=count,
                examples=tuple(examples[value]),
            )
            for value, count in sorted(counts.items())
        )

        return VariationPointSpec(
            name=dimension,
            source_attributes=(self._attribute,),
            variants=variants,
            total_observations=total_observations,
            missing_observations=missing_observations,
        )
