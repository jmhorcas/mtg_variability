
"""Protocols defining the contracts between variability analysis components."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, Sequence, runtime_checkable

from mtg_variability.variability.models import (
    VariationPointSpec,
    VariabilitySpecification,
)


# A card is represented as a mapping from CSV column names to values.
CardRecord = dict[str, str]


class CardDatasetReader(Protocol):
    """Reads card records from a dataset."""

    def read(self, path: Path) -> list[CardRecord]:
        """Reads all card records from the given CSV file."""
        ...


@runtime_checkable
class VariationExtractor(Protocol):
    """Extracts variation points from a collection of card records."""

    @property
    def name(self) -> str:
        """Returns the extractor's unique name."""
        ...

    def extract(
        self,
        records: Sequence[CardRecord],
    ) -> Sequence[VariationPointSpec]:
        """Extracts zero or more variation points from card records."""
        ...


class SpecificationWriter(Protocol):
    """Persists a variability specification."""

    def write(
        self,
        specification: VariabilitySpecification,
        path: Path,
    ) -> Path:
        """Writes a variability specification and returns its output path."""
        ...
