
"""Orchestration of the variability analysis pipeline."""

from pathlib import Path
from typing import Mapping

from mtg_variability.variability.extractors.registry import ExtractorRegistry
from mtg_variability.variability.models import VariabilitySpecification
from mtg_variability.variability.protocols import (
    CardDatasetReader,
    SpecificationWriter,
)


class VariabilityPipeline:
    """Coordinate dataset reading, variability extraction and persistence."""

    def __init__(
        self,
        reader: CardDatasetReader,
        registry: ExtractorRegistry,
        writer: SpecificationWriter,
    ) -> None:
        self._reader = reader
        self._registry = registry
        self._writer = writer

    def run(
        self,
        input_path: Path,
        output_path: Path,
        expansion_code: str,
        expansion_name: str,
        metadata: Mapping[str, object] | None = None,
    ) -> VariabilitySpecification:
        """Execute the variability analysis pipeline.

        Args:
            input_path: Path to the input dataset.
            output_path: Path where the specification will be written.
            expansion_code: Code identifying the expansion.
            expansion_name: Human-readable expansion name.
            metadata: Optional metadata for the resulting specification.

        Returns:
            The generated variability specification.

        Raises:
            Any exception raised by the reader, extractors or writer.
        """
        input_path = Path(input_path)
        output_path = Path(output_path)

        records = self._reader.read(input_path)

        variation_points = tuple(
            variation_point
            for extractor in self._registry
            for variation_point in extractor.extract(records)
        )

        specification = VariabilitySpecification(
            expansion_code=expansion_code,
            expansion_name=expansion_name,
            total_cards=len(records),
            variation_points=variation_points,
            metadata=dict(metadata) if metadata is not None else {},
        )

        self._writer.write(specification, output_path)

        return specification
