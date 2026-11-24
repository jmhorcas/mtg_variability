
"""Dataset profiling utilities for variability analysis."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from mtg_variability.variability.protocols import CardRecord


@dataclass(frozen=True, slots=True)
class AttributeProfile:
    """Statistical profile of a single dataset attribute."""

    name: str
    total_records: int
    missing_count: int
    value_counts: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Attribute name cannot be empty.")

        if self.total_records < 0:
            raise ValueError("Total records cannot be negative.")

        if not 0 <= self.missing_count <= self.total_records:
            raise ValueError(
                "Missing count must be between zero and total records."
            )

        counts = dict(self.value_counts)

        if any(count < 0 for count in counts.values()):
            raise ValueError("Value frequencies cannot be negative.")

        if sum(counts.values()) + self.missing_count != self.total_records:
            raise ValueError(
                "Value frequencies and missing count must add up "
                "to the total number of records."
            )

        object.__setattr__(self, "value_counts", counts)

    @property
    def distinct_count(self) -> int:
        """Returns the number of distinct non-missing values."""
        return len(self.value_counts)

    @property
    def non_missing_count(self) -> int:
        """Returns the number of records with a non-missing value."""
        return self.total_records - self.missing_count

    @property
    def missing_ratio(self) -> float:
        """Returns the proportion of missing values."""
        if self.total_records == 0:
            return 0.0

        return self.missing_count / self.total_records

    @property
    def value_ratio(self) -> float:
        """Returns the proportion of records with a non-missing value."""
        if self.total_records == 0:
            return 0.0

        return self.non_missing_count / self.total_records

    def most_common(self, limit: int | None = None) -> list[tuple[str, int]]:
        """Returns values ordered by descending frequency.

        Ties are resolved alphabetically for deterministic results.
        """
        values = sorted(
            self.value_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )

        if limit is not None:
            if limit < 0:
                raise ValueError("Limit cannot be negative.")

            values = values[:limit]

        return values


@dataclass(frozen=True, slots=True)
class DatasetProfile:
    """Statistical profile of a complete card dataset."""

    total_records: int
    attributes: Mapping[str, AttributeProfile] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if self.total_records < 0:
            raise ValueError("Total records cannot be negative.")

        attributes = dict(self.attributes)

        for name, profile in attributes.items():
            if name != profile.name:
                raise ValueError(
                    f"Attribute key '{name}' does not match "
                    f"profile name '{profile.name}'."
                )

            if profile.total_records != self.total_records:
                raise ValueError(
                    f"Attribute '{name}' has an inconsistent "
                    "number of records."
                )

        object.__setattr__(self, "attributes", attributes)

    @property
    def attribute_count(self) -> int:
        """Returns the number of attributes in the dataset."""
        return len(self.attributes)

    def get_attribute(self, name: str) -> AttributeProfile:
        """Returns the profile of an attribute.

        Raises:
            KeyError: If the attribute does not exist.
        """
        return self.attributes[name]


class DatasetProfiler:
    """Profiles the attributes and values of a card dataset."""

    def profile(
        self,
        records: Sequence[CardRecord],
    ) -> DatasetProfile:
        """Builds a statistical profile from card records.

        Empty strings and whitespace-only strings are treated as
        missing values. Non-empty values are counted exactly as
        they appear in the input records.

        Args:
            records: Card records loaded from a dataset.

        Returns:
            A profile containing statistics for every discovered
            attribute.
        """
        total_records = len(records)

        if not records:
            return DatasetProfile(total_records=0)

        attribute_names = self._get_attribute_names(records)

        attributes: dict[str, AttributeProfile] = {}

        for name in attribute_names:
            value_counts: Counter[str] = Counter()
            missing_count = 0

            for record in records:
                value = record.get(name, "")

                if not value or not value.strip():
                    missing_count += 1
                else:
                    value_counts[value] += 1

            attributes[name] = AttributeProfile(
                name=name,
                total_records=total_records,
                missing_count=missing_count,
                value_counts=dict(value_counts),
            )

        return DatasetProfile(
            total_records=total_records,
            attributes=attributes,
        )

    @staticmethod
    def _get_attribute_names(
        records: Sequence[CardRecord],
    ) -> list[str]:
        """Returns attribute names in their first-seen order."""
        names: dict[str, None] = {}

        for record in records:
            for name in record:
                names.setdefault(name, None)

        return list(names)
