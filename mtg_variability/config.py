
"""Project configuration loading and runtime setup."""

from __future__ import annotations

import logging
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    """Centralized configuration for the MTG variability pipeline."""

    data_dir: Path
    products_dir: Path
    expansions_file: Path
    variability_dir: Path
    taxonomy_path: Path
    uvl_output_dir: Path
    uvl_template_path: Path

    inspect_reports: bool = False
    print_reports: bool = False
    logging_level: str = "INFO"
    logging_file: Path | None = None

    @classmethod
    def from_toml(cls, config_path: Path) -> PipelineConfig:
        """Load configuration from a TOML file.

        Relative paths are resolved against the directory containing
        the configuration file.
        """
        config_path = Path(config_path).resolve()

        with config_path.open("rb") as config_file:
            raw_config = tomllib.load(config_file)

        base_dir = config_path.parent

        paths = cls._get_section(raw_config, "paths")
        inspection = cls._get_section(raw_config, "inspection")
        logging_config = cls._get_section(raw_config, "logging")

        def resolve_path(value: Any, name: str) -> Path:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"Configuration path {name!r} must be a non-empty string"
                )

            path = Path(value)
            if not path.is_absolute():
                path = base_dir / path

            return path.resolve()

        data_dir = resolve_path(
            paths.get("data_dir", "data"),
            "data_dir",
        )
        products_dir = resolve_path(
            paths.get("products_dir", "data/cards"),
            "products_dir",
        )
        expansions_file = resolve_path(
            paths.get(
                "expansions_file",
                "data/expansions/all_expansions.csv",
            ),
            "expansions_file",
        )
        variability_dir = resolve_path(
            paths.get("variability_dir", "data/variability"),
            "variability_dir",
        )
        taxonomy_path = resolve_path(
            paths.get(
                "taxonomy_path",
                "mtg_variability/data/taxonomy.json",
            ),
            "taxonomy_path",
        )
        uvl_output_dir = resolve_path(
            paths.get("uvl_output_dir", "uvl_models/generated"),
            "uvl_output_dir",
        )
        uvl_template_path = resolve_path(
            paths.get("uvl_template_path", "uvl_models/templates/base.uvl"),
            "uvl_template_path",
        )

        inspect_reports = inspection.get("inspect_reports", False)
        print_reports = inspection.get("print_reports", False)

        for name, value in (
            ("inspect_reports", inspect_reports),
            ("print_reports", print_reports),
        ):
            if not isinstance(value, bool):
                raise ValueError(f"{name} must be a boolean")

        logging_level = logging_config.get("level", "INFO")
        if not isinstance(logging_level, str):
            raise ValueError("logging.level must be a string")

        logging_level = logging_level.upper()
        if not isinstance(getattr(logging, logging_level, None), int):
            raise ValueError(f"Invalid logging level: {logging_level!r}")

        logging_file_value = logging_config.get("file", "")
        if not isinstance(logging_file_value, str):
            raise ValueError("logging.file must be a string")

        logging_file = (
            resolve_path(logging_file_value, "logging.file")
            if logging_file_value.strip()
            else None
        )

        return cls(
            data_dir=data_dir,
            products_dir=products_dir,
            expansions_file=expansions_file,
            variability_dir=variability_dir,
            taxonomy_path=taxonomy_path,
            uvl_output_dir=uvl_output_dir,
            uvl_template_path=uvl_template_path,
            inspect_reports=inspect_reports,
            print_reports=print_reports,
            logging_level=logging_level,
            logging_file=logging_file,
        )

    @staticmethod
    def _get_section(
        config: dict[str, Any],
        section_name: str,
    ) -> dict[str, Any]:
        """Return a TOML section, validating its type."""
        section = config.get(section_name, {})

        if not isinstance(section, dict):
            raise ValueError(
                f"Configuration section {section_name!r} must be a table"
            )

        return section

    def ensure_directories(self) -> None:
        """Create directories used to store pipeline outputs."""
        directories = (
            self.data_dir,
            self.products_dir,
            self.expansions_file.parent,
            self.variability_dir,
            self.uvl_output_dir,
        )

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def configure_logging(self) -> None:
        """Configure application logging."""
        level = getattr(logging, self.logging_level)

        handlers: list[logging.Handler] = [
            logging.StreamHandler(),
        ]

        if self.logging_file is not None:
            self.logging_file.parent.mkdir(parents=True, exist_ok=True)
            handlers.append(
                logging.FileHandler(self.logging_file, encoding="utf-8")
            )

        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            handlers=handlers,
        )
