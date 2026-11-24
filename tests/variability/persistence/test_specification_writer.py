
"""Tests for JSONSpecificationWriter."""

import json
from pathlib import Path

import pytest

from mtg_variability.variability.models import (
    VariabilitySpecification,
    VariationPointSpec,
    VariantSpec,
)
from mtg_variability.variability.persistence.specification_writer import JSONSpecificationWriter


@pytest.fixture
def writer() -> JSONSpecificationWriter:
    return JSONSpecificationWriter()


@pytest.fixture
def specification() -> VariabilitySpecification:
    return VariabilitySpecification(
        expansion_code="example",
        expansion_name="Example Expansion",
        total_cards=2,
        variation_points=(
            VariationPointSpec(
                name="rarity",
                source_attributes=("rarity",),
                variants=(
                    VariantSpec(
                        name="Common",
                        occurrences=1,
                        examples=("Card A",),
                    ),
                    VariantSpec(
                        name="Rare",
                        occurrences=1,
                        examples=("Card B",),
                    ),
                ),
                total_observations=2,
                missing_observations=0,
            ),
        ),
        metadata={"source": "test"},
    )


def test_writes_valid_json(
    writer: JSONSpecificationWriter,
    specification: VariabilitySpecification,
    tmp_path: Path,
) -> None:
    path = tmp_path / "specification.json"

    result = writer.write(specification, path)

    assert result == path
    assert path.is_file()

    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["schema_version"] == 1
    assert data["expansion_code"] == "example"
    assert data["expansion_name"] == "Example Expansion"
    assert data["total_cards"] == 2
    assert len(data["variation_points"]) == 1


def test_serializes_nested_dataclasses(
    writer: JSONSpecificationWriter,
    specification: VariabilitySpecification,
    tmp_path: Path,
) -> None:
    path = tmp_path / "specification.json"

    writer.write(specification, path)

    data = json.loads(path.read_text(encoding="utf-8"))
    rarity = data["variation_points"][0]

    assert rarity["name"] == "rarity"
    assert rarity["source_attributes"] == ["rarity"]
    assert rarity["total_observations"] == 2

    assert rarity["variants"] == [
        {
            "name": "Common",
            "occurrences": 1,
            "child_points": [],
            "examples": ["Card A"],
            "metadata": {},
        },
        {
            "name": "Rare",
            "occurrences": 1,
            "child_points": [],
            "examples": ["Card B"],
            "metadata": {},
        },
    ]


def test_preserves_unicode(
    writer: JSONSpecificationWriter,
    tmp_path: Path,
) -> None:
    specification = VariabilitySpecification(
        expansion_code="test",
        expansion_name="Serra’s Realm",
        total_cards=1,
        variation_points=(),
    )
    path = tmp_path / "specification.json"

    writer.write(specification, path)

    content = path.read_text(encoding="utf-8")

    assert "Serra’s Realm" in content
    assert "\\u2019" not in content


def test_creates_parent_directories(
    writer: JSONSpecificationWriter,
    specification: VariabilitySpecification,
    tmp_path: Path,
) -> None:
    path = tmp_path / "nested" / "output" / "specification.json"

    writer.write(specification, path)

    assert path.is_file()


def test_writes_deterministic_output(
    writer: JSONSpecificationWriter,
    tmp_path: Path,
) -> None:
    first = VariabilitySpecification(
        expansion_code="test",
        expansion_name="Test",
        total_cards=1,
        variation_points=(),
        metadata={"z": 1, "a": 2},
    )
    second = VariabilitySpecification(
        expansion_code="test",
        expansion_name="Test",
        total_cards=1,
        variation_points=(),
        metadata={"a": 2, "z": 1},
    )

    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"

    writer.write(first, first_path)
    writer.write(second, second_path)

    assert first_path.read_bytes() == second_path.read_bytes()


def test_overwrites_existing_file(
    writer: JSONSpecificationWriter,
    specification: VariabilitySpecification,
    tmp_path: Path,
) -> None:
    path = tmp_path / "specification.json"
    path.write_text("previous content", encoding="utf-8")

    writer.write(specification, path)

    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["expansion_code"] == specification.expansion_code


def test_preserves_existing_file_on_serialization_error(
    writer: JSONSpecificationWriter,
    tmp_path: Path,
) -> None:
    specification = VariabilitySpecification(
        expansion_code="test",
        expansion_name="Test",
        total_cards=1,
        variation_points=(),
        metadata={"unsupported": object()},
    )
    path = tmp_path / "specification.json"
    path.write_text("previous content", encoding="utf-8")

    with pytest.raises(TypeError):
        writer.write(specification, path)

    assert path.read_text(encoding="utf-8") == "previous content"
    assert list(tmp_path.glob(".specification.json.*.tmp")) == []


def test_rejects_invalid_specification(
    writer: JSONSpecificationWriter,
    tmp_path: Path,
) -> None:
    path = tmp_path / "specification.json"

    with pytest.raises(TypeError, match="VariabilitySpecification"):
        writer.write({"expansion_code": "test"}, path)  # type: ignore[arg-type]

    assert not path.exists()


def test_returns_destination_path(
    writer: JSONSpecificationWriter,
    specification: VariabilitySpecification,
    tmp_path: Path,
) -> None:
    path = tmp_path / "specification.json"

    result = writer.write(specification, path)

    assert isinstance(result, Path)
    assert result == path
