
"""Power and toughness variation extraction."""

from collections import Counter, defaultdict
from collections.abc import Sequence

from mtg_variability.variability.extractors.base import BaseVariationExtractor
from mtg_variability.variability.models import VariantSpec, VariationPointSpec
from mtg_variability.variability.protocols import CardRecord


class PowerToughnessExtractor(BaseVariationExtractor):
    """Extract power and toughness variation from card records.

    Power and toughness are treated as independent categorical dimensions.
    Values are preserved as strings because MTG supports both numeric and
    symbolic expressions, such as '*', 'X', and '1+*'.
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

        for record in records:
            value = self._get_normalized_value(record, attribute)

            if self._is_missing(value):
                missing_count += 1
                continue

            counts[value] += 1

            example = self._get_normalized_value(
                record,
                self._example_attribute,
            )
            self._append_example(examples[value], example)

        # Constant attributes do not represent variation points.
        if len(counts) < 2:
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

        return VariationPointSpec(
            name=attribute,
            source_attributes=(attribute,),
            variants=variants,
            total_observations=len(records),
            missing_observations=missing_count,
        )

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
