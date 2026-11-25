
"""Variability specification loading for feature model construction."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SpecificationLoader:
    """Load Phase 2 variability specifications from JSON files.

    The loader returns the original JSON structures as Python dictionaries.
    It does not create intermediate domain models or transform the data.
    """

    REQUIRED_FIELDS = {
        "schema_version",
        "expansion_code",
        "expansion_name",
        "total_cards",
        "variation_points",
    }

    SUPPORTED_SCHEMA_VERSION = 1

    def __init__(self, specifications_dir: Path) -> None:
        """Initialize the loader.

        Args:
            specifications_dir: Directory containing Phase 2 JSON files.
        """
        self.specifications_dir = Path(specifications_dir)

    def load_expansion(self, expansion_code: str) -> dict[str, Any]:
        """Load the variability specification of one expansion.

        Args:
            expansion_code: Code identifying the expansion.

        Returns:
            The expansion specification as a dictionary.

        Raises:
            ValueError: If the expansion code is invalid or the JSON
                specification is malformed.
            FileNotFoundError: If the specification file does not exist.
        """
        if (
            not isinstance(expansion_code, str)
            or not expansion_code.strip()
            or Path(expansion_code).name != expansion_code
        ):
            raise ValueError("Invalid expansion code")

        specification_path = (
            self.specifications_dir / f"{expansion_code}.json"
        )

        specification = self._load_file(specification_path)

        if specification["expansion_code"] != expansion_code:
            raise ValueError(
                f"Expansion code mismatch in {specification_path}: "
                f"expected {expansion_code!r}, "
                f"found {specification['expansion_code']!r}"
            )

        return specification

    def load_all(self) -> list[dict[str, Any]]:
        """Load all available variability specifications.

        Files are processed in alphabetical order to ensure deterministic
        results.

        Returns:
            A list containing the specifications of all expansions.

        Raises:
            FileNotFoundError: If the specifications directory does not
                exist or contains no JSON specifications.
        """
        if not self.specifications_dir.is_dir():
            raise FileNotFoundError(
                "Variability specifications directory does not exist: "
                f"{self.specifications_dir}"
            )

        specification_files = sorted(
            self.specifications_dir.glob("*.json")
        )

        if not specification_files:
            raise FileNotFoundError(
                "No variability specifications found in: "
                f"{self.specifications_dir}"
            )

        return [
            self._load_file(path)
            for path in specification_files
        ]

    def _load_file(self, path: Path) -> dict[str, Any]:
        """Load and perform basic structural validation of a JSON file.

        Args:
            path: Path to the JSON specification.

        Returns:
            The parsed JSON object.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the JSON is malformed or has an unsupported
                structure or schema version.
        """
        if not path.is_file():
            raise FileNotFoundError(
                f"Variability specification not found: {path}"
            )

        try:
            with path.open("r", encoding="utf-8") as file:
                specification = json.load(file)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Invalid JSON in variability specification {path}: "
                f"{error}"
            ) from error

        if not isinstance(specification, dict):
            raise ValueError(
                f"Invalid variability specification in {path}: "
                "expected a JSON object"
            )

        missing_fields = self.REQUIRED_FIELDS - specification.keys()

        if missing_fields:
            raise ValueError(
                f"Invalid variability specification in {path}: "
                f"missing required fields {sorted(missing_fields)}"
            )

        schema_version = specification["schema_version"]

        if (
            isinstance(schema_version, bool)
            or not isinstance(schema_version, int)
            or schema_version != self.SUPPORTED_SCHEMA_VERSION
        ):
            raise ValueError(
                f"Unsupported schema version in {path}: "
                f"{schema_version!r}"
            )

        if not isinstance(specification["expansion_code"], str):
            raise ValueError(
                f"Invalid expansion_code in {path}: expected a string"
            )

        if not isinstance(specification["expansion_name"], str):
            raise ValueError(
                f"Invalid expansion_name in {path}: expected a string"
            )

        if (
            isinstance(specification["total_cards"], bool)
            or not isinstance(specification["total_cards"], int)
            or specification["total_cards"] < 0
        ):
            raise ValueError(
                f"Invalid total_cards in {path}: "
                "expected a non-negative integer"
            )

        if not isinstance(specification["variation_points"], list):
            raise ValueError(
                f"Invalid variation_points in {path}: expected a list"
            )

        return specification
