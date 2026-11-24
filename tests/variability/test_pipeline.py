
"""Tests for VariabilityPipeline."""

from pathlib import Path

import pytest

from mtg_variability.variability.extractors.registry import ExtractorRegistry
from mtg_variability.variability.models import (
    VariationPointSpec,
    VariabilitySpecification,
)
from mtg_variability.variability.pipeline import VariabilityPipeline


class FakeDatasetReader:
    """In-memory dataset reader for testing."""

    def __init__(self, records: list[dict[str, str]]) -> None:
        self.records = records
        self.received_path: Path | None = None

    def read(self, path: Path) -> list[dict[str, str]]:
        self.received_path = path
        return self.records


class FakeSpecificationWriter:
    """Specification writer that stores the last written specification."""

    def __init__(self) -> None:
        self.specification: VariabilitySpecification | None = None
        self.received_path: Path | None = None

    def write(
        self,
        specification: VariabilitySpecification,
        path: Path,
    ) -> Path:
        self.specification = specification
        self.received_path = path
        return path


class FakeExtractor:
    """Extractor returning predefined variation points."""

    def __init__(
        self,
        variation_points: tuple[VariationPointSpec, ...],
        name: str = "fake",
    ) -> None:
        self.variation_points = variation_points
        self._name = name
        self.received_records: list[dict[str, str]] | None = None

    @property
    def name(self) -> str:
        return self._name

    def extract(
        self,
        records: list[dict[str, str]],
    ) -> tuple[VariationPointSpec, ...]:
        self.received_records = records
        return self.variation_points


@pytest.fixture
def variation_point() -> VariationPointSpec:
    return VariationPointSpec(
        name="rarity",
        source_attributes=("rarity",),
        total_observations=2,
        variants=(),
    )


@pytest.fixture
def records() -> list[dict[str, str]]:
    return [
        {"name": "Card A", "rarity": "Common"},
        {"name": "Card B", "rarity": "Rare"},
    ]


def test_runs_complete_pipeline(
    records: list[dict[str, str]],
    variation_point: VariationPointSpec,
    tmp_path: Path,
) -> None:
    reader = FakeDatasetReader(records)
    writer = FakeSpecificationWriter()
    extractor = FakeExtractor((variation_point,))

    registry = ExtractorRegistry()
    registry.register(extractor)

    pipeline = VariabilityPipeline(reader, registry, writer)

    input_path = tmp_path / "cards.csv"
    output_path = tmp_path / "specification.json"

    specification = pipeline.run(
        input_path=input_path,
        output_path=output_path,
        expansion_code="example",
        expansion_name="Example Expansion",
    )

    assert isinstance(specification, VariabilitySpecification)
    assert specification.expansion_code == "example"
    assert specification.expansion_name == "Example Expansion"
    assert specification.total_cards == 2
    assert specification.variation_points == (variation_point,)

    assert reader.received_path == input_path
    assert extractor.received_records is records
    assert writer.specification is specification
    assert writer.received_path == output_path


def test_includes_custom_metadata(
    records: list[dict[str, str]],
    tmp_path: Path,
) -> None:
    reader = FakeDatasetReader(records)
    writer = FakeSpecificationWriter()
    registry = ExtractorRegistry()

    pipeline = VariabilityPipeline(reader, registry, writer)

    specification = pipeline.run(
        input_path=tmp_path / "cards.csv",
        output_path=tmp_path / "specification.json",
        expansion_code="example",
        expansion_name="Example Expansion",
        metadata={"source": "test", "version": 1},
    )

    assert specification.metadata == {
        "source": "test",
        "version": 1,
    }


def test_uses_empty_metadata_by_default(
    records: list[dict[str, str]],
    tmp_path: Path,
) -> None:
    reader = FakeDatasetReader(records)
    writer = FakeSpecificationWriter()
    registry = ExtractorRegistry()

    pipeline = VariabilityPipeline(reader, registry, writer)

    specification = pipeline.run(
        input_path=tmp_path / "cards.csv",
        output_path=tmp_path / "specification.json",
        expansion_code="example",
        expansion_name="Example Expansion",
    )

    assert specification.metadata == {}


def test_supports_empty_dataset(tmp_path: Path) -> None:
    reader = FakeDatasetReader([])
    writer = FakeSpecificationWriter()
    registry = ExtractorRegistry()

    pipeline = VariabilityPipeline(reader, registry, writer)

    specification = pipeline.run(
        input_path=tmp_path / "cards.csv",
        output_path=tmp_path / "specification.json",
        expansion_code="empty",
        expansion_name="Empty Expansion",
    )

    assert specification.total_cards == 0
    assert specification.variation_points == ()
    assert writer.specification is specification


def test_supports_multiple_extractors(
    records: list[dict[str, str]],
    tmp_path: Path,
) -> None:
    first_point = VariationPointSpec(
        name="rarity",
        source_attributes=("rarity",),
    )
    second_point = VariationPointSpec(
        name="color",
        source_attributes=("colors",),
    )

    first_extractor = FakeExtractor((first_point,), name="rarity")
    second_extractor = FakeExtractor((second_point,), name="color")

    registry = ExtractorRegistry()
    registry.register(first_extractor)
    registry.register(second_extractor)

    reader = FakeDatasetReader(records)
    writer = FakeSpecificationWriter()

    pipeline = VariabilityPipeline(reader, registry, writer)

    specification = pipeline.run(
        input_path=tmp_path / "cards.csv",
        output_path=tmp_path / "specification.json",
        expansion_code="example",
        expansion_name="Example Expansion",
    )

    assert specification.variation_points == (
        first_point,
        second_point,
    )


def test_propagates_reader_errors(tmp_path: Path) -> None:
    class FailingReader:
        def read(self, path: Path) -> list[dict[str, str]]:
            raise RuntimeError("Dataset reading failed.")

    writer = FakeSpecificationWriter()
    registry = ExtractorRegistry()

    pipeline = VariabilityPipeline(
        FailingReader(),
        registry,
        writer,
    )

    with pytest.raises(RuntimeError, match="Dataset reading failed"):
        pipeline.run(
            input_path=tmp_path / "cards.csv",
            output_path=tmp_path / "specification.json",
            expansion_code="example",
            expansion_name="Example Expansion",
        )

    assert writer.specification is None


def test_propagates_writer_errors(
    records: list[dict[str, str]],
    tmp_path: Path,
) -> None:
    class FailingWriter:
        def write(
            self,
            specification: VariabilitySpecification,
            path: Path,
        ) -> Path:
            raise OSError("Specification writing failed.")

    pipeline = VariabilityPipeline(
        FakeDatasetReader(records),
        ExtractorRegistry(),
        FailingWriter(),
    )

    with pytest.raises(OSError, match="Specification writing failed"):
        pipeline.run(
            input_path=tmp_path / "cards.csv",
            output_path=tmp_path / "specification.json",
            expansion_code="example",
            expansion_name="Example Expansion",
        )


def test_converts_string_paths_to_path_objects(
    records: list[dict[str, str]],
) -> None:
    reader = FakeDatasetReader(records)
    writer = FakeSpecificationWriter()
    registry = ExtractorRegistry()

    pipeline = VariabilityPipeline(reader, registry, writer)

    pipeline.run(
        input_path="data/cards.csv",  # type: ignore[arg-type]
        output_path="output/specification.json",  # type: ignore[arg-type]
        expansion_code="example",
        expansion_name="Example Expansion",
    )

    assert reader.received_path == Path("data/cards.csv")
    assert writer.received_path == Path("output/specification.json")
