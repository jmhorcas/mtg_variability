
import json

import pytest

from mtg_variability.feature_model.specification_loader import (
    SpecificationLoader,
)


@pytest.fixture
def specifications_dir(tmp_path):
    return tmp_path


@pytest.fixture
def specification():
    return {
        "schema_version": 1,
        "expansion_code": "LEA",
        "expansion_name": "Limited Edition Alpha",
        "metadata": {},
        "total_cards": 295,
        "variation_points": [
            {
                "name": "rarity",
                "category": "collection",
                "source_attributes": ["rarity"],
                "total_observations": 295,
                "missing_observations": 0,
                "variants": [
                    {
                        "name": "common",
                        "occurrences": 74,
                        "examples": [],
                        "metadata": {},
                        "child_points": [],
                    },
                    {
                        "name": "rare",
                        "occurrences": 88,
                        "examples": [],
                        "metadata": {},
                        "child_points": [],
                    },
                ],
                "child_points": [],
                "metadata": {},
            }
        ],
    }


def _write_specification(directory, specification):
    path = directory / f"{specification['expansion_code']}.json"

    path.write_text(
        json.dumps(specification),
        encoding="utf-8",
    )

    return path


def test_loads_expansion(
    specifications_dir,
    specification,
):
    _write_specification(specifications_dir, specification)

    loader = SpecificationLoader(specifications_dir)

    result = loader.load_expansion("LEA")

    assert result == specification
    assert result["expansion_code"] == "LEA"


def test_loads_all_expansions(
    specifications_dir,
    specification,
):
    _write_specification(specifications_dir, specification)

    second = {
        **specification,
        "expansion_code": "LEB",
        "expansion_name": "Limited Edition Beta",
    }

    _write_specification(specifications_dir, second)

    loader = SpecificationLoader(specifications_dir)

    result = loader.load_all()

    assert len(result) == 2
    assert [item["expansion_code"] for item in result] == [
        "LEA",
        "LEB",
    ]


def test_load_expansion_rejects_invalid_code(
    specifications_dir,
):
    loader = SpecificationLoader(specifications_dir)

    with pytest.raises(ValueError, match="Invalid expansion code"):
        loader.load_expansion("../LEA")


def test_load_expansion_raises_when_file_does_not_exist(
    specifications_dir,
):
    loader = SpecificationLoader(specifications_dir)

    with pytest.raises(FileNotFoundError):
        loader.load_expansion("LEA")


def test_load_all_raises_when_directory_is_empty(
    specifications_dir,
):
    loader = SpecificationLoader(specifications_dir)

    with pytest.raises(FileNotFoundError):
        loader.load_all()


def test_rejects_unsupported_schema_version(
    specifications_dir,
    specification,
):
    specification["schema_version"] = 2
    _write_specification(specifications_dir, specification)

    loader = SpecificationLoader(specifications_dir)

    with pytest.raises(ValueError, match="Unsupported schema version"):
        loader.load_expansion("LEA")


def test_rejects_missing_required_fields(
    specifications_dir,
    specification,
):
    del specification["variation_points"]
    _write_specification(specifications_dir, specification)

    loader = SpecificationLoader(specifications_dir)

    with pytest.raises(ValueError, match="missing required fields"):
        loader.load_expansion("LEA")


def test_rejects_mismatched_expansion_code(
    specifications_dir,
    specification,
):
    # Store a specification with an inconsistent expansion code.
    specification["expansion_code"] = "LEB"

    path = specifications_dir / "LEA.json"
    path.write_text(
        json.dumps(specification),
        encoding="utf-8",
    )

    loader = SpecificationLoader(specifications_dir)

    with pytest.raises(ValueError, match="Expansion code mismatch"):
        loader.load_expansion("LEA")