
"""Power and toughness variation extraction."""

from collections import Counter, defaultdict
from collections.abc import Sequence

from mtg_variability.variability.extractors.base import BaseVariationExtractor
from mtg_variability.variability.models import (
    VariationPointSpec,
    VariationStatistics,
    VariantSpec,
)
from mtg_variability.variability.protocols import CardRecord


class PowerToughnessExtractor(BaseVariationExtractor):
    """Extract power and toughness variation from card records.

    Values are preserved as strings because MTG supports both numeric and
    symbolic expressions, such as '*', 'X', and '1+*'.

    Integer values are additionally summarized using numeric bounds.
    Non-integer values are retained as special values.
    """

    def __init__(
        self,
        power_attribute: str = "power",
        toughness_attribute: str = "toughness",
        example_attribute: str = "name",
        max_examples: int = 3,
    ) -> None:
        if not power_attribute.strip():
            raise ValueError("power_attribute cannot be empty.")
        if not toughness_attribute.strip():
            raise ValueError("toughness_attribute cannot be empty.")
        if power_attribute == toughness_attribute:
            raise ValueError("Power and toughness attributes must be different.")
        if not example_attribute.strip():
            raise ValueError("example_attribute cannot be empty.")
        if max_examples < 0:
            raise ValueError("max_examples cannot be negative.")

        self._power_attribute = power_attribute
        self._toughness_attribute = toughness_attribute
        self._example_attribute = example_attribute
        self._max_examples = max_examples

    @property
    def name(self) -> str:
        """Return the extractor identifier."""
        return "power-toughness"

    def _extract(
        self,
        records: Sequence[CardRecord],
    ) -> Sequence[VariationPointSpec]:
        variation_points = []

        for attribute in (
            self._power_attribute,
            self._toughness_attribute,
        ):
            point = self._extract_attribute(records, attribute)
            if point is not None:
                variation_points.append(point)

        return tuple(variation_points)

    def _extract_attribute(
        self,
        records: Sequence[CardRecord],
        attribute: str,
    ) -> VariationPointSpec | None:
        """Extract one power or toughness variation point."""
        counts: Counter[str] = Counter()
        examples: dict[str, list[str]] = defaultdict(list)
        missing_count = 0

        numeric_values: list[int] = []
        special_values: set[str] = set()

        for record in records:
            value = self._get_normalized_value(record, attribute)

            if self._is_missing(value):
                missing_count += 1
                continue

            counts[value] += 1

            numeric_value = self._parse_integer(value)

            if numeric_value is None:
                special_values.add(value)
            else:
                numeric_values.append(numeric_value)

            example = self._get_normalized_value(
                record,
                self._example_attribute,
            )
            self._append_example(examples[value], example)

        # Skip attributes that are constant and always present.
        if len(counts) < 2 and missing_count == 0:
            return None

        variants = tuple(
            VariantSpec(
                name=value,
                occurrences=count,
                examples=tuple(examples[value]),
            )
            for value, count in sorted(
                counts.items(),
                key=lambda item: (item[0].casefold(), item[0]),
            )
        )

        statistics = VariationStatistics(
            numeric_minimum=min(numeric_values) if numeric_values else None,
            numeric_maximum=max(numeric_values) if numeric_values else None,
            special_values=tuple(
                sorted(special_values, key=lambda value: (value.casefold(), value))
            ),
        )

        return VariationPointSpec(
            name=attribute,
            source_attributes=(attribute,),
            variants=variants,
            total_observations=len(records),
            missing_observations=missing_count,
            statistics=statistics,
        )

    @staticmethod
    def _parse_integer(value: str) -> int | None:
        """Parse an integer value, returning None for symbolic values."""
        try:
            return int(value)
        except ValueError:
            return None

    def _append_example(
        self,
        examples: list[str],
        example: str,
    ) -> None:
        """Append a distinct example without exceeding the configured limit."""
        if (
            example
            and example not in examples
            and len(examples) < self._max_examples
        ):
            examples.append(example)
