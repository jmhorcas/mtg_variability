
"""Phase 2: Discover and analyze variability in MTG expansions."""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path
from typing import Sequence

from mtg_variability.config import PipelineConfig
from mtg_variability.utils.timer import Timer
from mtg_variability.variability.extractors import (
    CategoricalExtractor,
    ExtractorRegistry,
    ManaCostExtractor,
    MultiValueExtractor,
    PowerToughnessExtractor,
    TypeSystemExtractor,
)
from mtg_variability.variability.persistence.csv_reader import (
    CSVCardDatasetReader,
)
from mtg_variability.variability.persistence.specification_writer import (
    JSONSpecificationWriter,
)
from mtg_variability.variability.pipeline import VariabilityPipeline
from mtg_variability.variability.taxonomy.loader import load_taxonomy

logger = logging.getLogger(__name__)


def _read_expansions(expansions_file: Path) -> list[tuple[str, str]]:
    """Read expansion codes and names from the expansion catalog."""
    if not expansions_file.is_file():
        raise FileNotFoundError(
            f"Expansion catalog not found: {expansions_file}"
        )

    expansions: list[tuple[str, str]] = []
    seen_codes: set[str] = set()

    with expansions_file.open(
        mode="r",
        encoding="utf-8-sig",
        newline="",
    ) as csv_file:
        reader = csv.DictReader(csv_file)

        if not reader.fieldnames:
            raise ValueError(
                f"Expansion catalog has no header: {expansions_file}"
            )

        required_fields = {"code", "name"}
        missing_fields = required_fields - set(reader.fieldnames)

        if missing_fields:
            raise ValueError(
                "Expansion catalog is missing required columns: "
                f"{', '.join(sorted(missing_fields))}"
            )

        for row_number, row in enumerate(reader, start=2):
            code = (row.get("code") or "").strip()
            name = (row.get("name") or "").strip()

            if not code or not name:
                logger.warning(
                    "Skipping expansion catalog row %d: "
                    "missing code or name",
                    row_number,
                )
                continue

            normalized_code = code.upper()

            if normalized_code in seen_codes:
                logger.warning(
                    "Skipping duplicate expansion code %s "
                    "in catalog row %d",
                    code,
                    row_number,
                )
                continue

            seen_codes.add(normalized_code)
            expansions.append((code, name))

    return expansions


def _find_expansion_csv(
    products_dir: Path,
    expansion_code: str,
) -> Path | None:
    """Find the CSV file associated with an expansion.

    CSV filenames include a numeric prefix assigned during Phase 1.
    """
    matches = sorted(
        products_dir.glob(f"????-{expansion_code}-*.csv")
    )

    if not matches:
        return None

    if len(matches) > 1:
        raise ValueError(
            f"Multiple CSV files found for expansion {expansion_code}: "
            f"{', '.join(path.name for path in matches)}"
        )

    return matches[0]


def _build_extractor_registry(config: PipelineConfig) -> ExtractorRegistry:
    """Create and configure all variability extractors."""
    taxonomy = load_taxonomy(config.taxonomy_path)

    registry = ExtractorRegistry()

    # Functional variability.
    registry.register(
        CategoricalExtractor(
            attribute="layout",
            category="functional",
        )
    )
    registry.register(
        MultiValueExtractor(attribute="colors")
    )
    registry.register(
        MultiValueExtractor(attribute="color_identity")
    )
    registry.register(
        TypeSystemExtractor(taxonomy=taxonomy)
    )
    registry.register(PowerToughnessExtractor())
    registry.register(
        ManaCostExtractor(attribute="mana_cost")
    )

    # Collection variability.
    registry.register(
        CategoricalExtractor(
            attribute="rarity",
            category="collection",
        )
    )

    # Presentation variability.
    registry.register(
        CategoricalExtractor(
            attribute="watermark",
            category="presentation",
        )
    )
    registry.register(
        CategoricalExtractor(
            attribute="border",
            category="presentation",
        )
    )

    return registry


def _process_expansion(
    pipeline: VariabilityPipeline,
    expansion_code: str,
    expansion_name: str,
    input_path: Path,
    output_path: Path,
) -> None:
    """Run variability analysis for a single expansion."""
    logger.info(
        "Processing expansion %s (%s)",
        expansion_code,
        expansion_name,
    )

    with Timer(
        message=f"Variability analysis for {expansion_code}",
        logger=logger.info,
    ):
        specification = pipeline.run(
            input_path=input_path,
            output_path=output_path,
            expansion_code=expansion_code,
            expansion_name=expansion_name,
        )

    logger.info(
        "Expansion %s completed: %d cards, %d variation points",
        expansion_code,
        specification.total_cards,
        len(specification.variation_points),
    )
    logger.info("Specification saved to %s", output_path)


def run_phase2(
    config: PipelineConfig,
    expansion_code: str | None = None,
) -> list[str]:
    """Execute Phase 2 for one expansion or all available expansions.

    Args:
        config: Project configuration.
        expansion_code: Expansion code to process. If omitted, all
            expansions in the catalog are considered.

    Returns:
        A list of expansion codes that could not be processed.

    Raises:
        FileNotFoundError: If the expansion catalog or taxonomy is missing.
        ValueError: If the requested expansion does not exist in the catalog.
    """
    config.ensure_directories()

    expansions = _read_expansions(config.expansions_file)

    if expansion_code is not None:
        requested_code = expansion_code.strip().upper()

        if not requested_code:
            raise ValueError("Expansion code cannot be empty")

        expansions = [
            (code, name)
            for code, name in expansions
            if code.upper() == requested_code
        ]

        if not expansions:
            raise ValueError(
                f"Expansion {requested_code!r} was not found "
                f"in {config.expansions_file}"
            )

    if not expansions:
        logger.warning("No expansions found in the expansion catalog")
        return []

    logger.info(
        "=== Phase 2: Analyzing %d expansion(s) ===",
        len(expansions),
    )

    registry = _build_extractor_registry(config)

    reader = CSVCardDatasetReader()
    writer = JSONSpecificationWriter()

    pipeline = VariabilityPipeline(
        reader=reader,
        registry=registry,
        writer=writer,
    )

    failed_expansions: list[str] = []
    processed_expansions = 0

    with Timer(
        message="Total variability analysis time",
        logger=logger.info,
    ):
        for code, name in expansions:
            try:
                input_path = _find_expansion_csv(
                    config.products_dir,
                    code,
                )

                if input_path is None:
                    logger.warning(
                        "Skipping expansion %s: no matching CSV found "
                        "in %s",
                        code,
                        config.products_dir,
                    )
                    failed_expansions.append(code)
                    continue

                output_path = config.variability_dir / f"{code}.json"

                _process_expansion(
                    pipeline=pipeline,
                    expansion_code=code,
                    expansion_name=name,
                    input_path=input_path,
                    output_path=output_path,
                )

                processed_expansions += 1

            except Exception:
                logger.exception(
                    "Failed to process expansion %s",
                    code,
                )
                failed_expansions.append(code)

    logger.info("=== Phase 2 summary ===")
    logger.info("Expansions found: %d", len(expansions))
    logger.info("Successfully processed: %d", processed_expansions)
    logger.info("Failed or skipped: %d", len(failed_expansions))

    if failed_expansions:
        logger.warning(
            "Failed expansions: %s",
            ", ".join(failed_expansions),
        )

    return failed_expansions


def main(argv: Sequence[str] | None = None) -> int:
    """Parse command-line arguments and execute Phase 2."""
    parser = argparse.ArgumentParser(
        description=(
            "Analyze variability in Magic: The Gathering expansions."
        )
    )

    parser.add_argument(
        "expansion_code",
        nargs="?",
        help="Code of the expansion to process (e.g. MKM).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all expansions in the catalog (default).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.toml"),
        help="Path to the TOML configuration file.",
    )

    args = parser.parse_args(argv)

    if args.all and args.expansion_code is not None:
        parser.error(
            "Specify either an expansion code or --all, not both."
        )

    try:
        config = PipelineConfig.from_toml(args.config)
        config.configure_logging()

        failed_expansions = run_phase2(
            config=config,
            expansion_code=(
                args.expansion_code
                if not args.all
                else None
            ),
        )

        return 1 if failed_expansions else 0

    except (FileNotFoundError, ValueError) as error:
        logger.error("Phase 2 failed: %s", error)
        return 1


if __name__ == "__main__":
    sys.exit(main())
