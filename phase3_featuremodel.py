
"""Phase 3: feature model construction and integration."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Mapping, Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any

from flamapy.metamodels.fm_metamodel.transformations import (
    UVLReader,
    UVLWriter,
)

from mtg_variability.config import PipelineConfig
from mtg_variability.feature_model.builder import FeatureModelBuilder
from mtg_variability.feature_model.specification_loader import (
    SpecificationLoader,
)


logger = logging.getLogger(__name__)


def run_phase3(
    config_path: str | Path = "config.toml",
    expansion_code: str | None = None,
) -> list[Path]:
    """Run Phase 3 for one expansion or for all available expansions."""
    config = PipelineConfig.from_toml(config_path)
    config.ensure_directories()

    if hasattr(config, "configure_logging"):
        config.configure_logging()

    loader = SpecificationLoader(config.variability_dir)

    logger.info("Loading feature model template: %s", config.uvl_template_path)
    template_model = UVLReader(str(config.uvl_template_path)).transform()

    builder = FeatureModelBuilder(template_model)
    output_paths: list[Path] = []

    if expansion_code is not None:
        logger.info("Building feature model for expansion %s", expansion_code)

        specification = loader.load_expansion(expansion_code)
        feature_model = builder.build(specification)

        output_path = _output_path(config.uvl_output_dir, expansion_code)
        _write_feature_model(feature_model, output_path)
        output_paths.append(output_path)

        return output_paths

    specifications = _load_all_specifications(loader)

    if not specifications:
        logger.warning("No variability specifications were found.")
        return output_paths

    for specification in specifications:
        code = specification.get("expansion_code")

        if not isinstance(code, str) or not code.strip():
            raise ValueError(
                "Every variability specification must have an expansion_code."
            )

        logger.info("Building feature model for expansion %s", code)

        feature_model = builder.build(specification)
        output_path = _output_path(config.uvl_output_dir, code)

        _write_feature_model(feature_model, output_path)
        output_paths.append(output_path)

    logger.info("Building global feature model.")

    global_specification = _merge_specifications(specifications)
    global_model = builder.build(global_specification)

    global_path = _output_path(config.uvl_output_dir, "ALL_EXPANSIONS")
    _write_feature_model(global_model, global_path)
    output_paths.append(global_path)

    return output_paths


def _load_all_specifications(
    loader: SpecificationLoader,
) -> list[Mapping[str, Any]]:
    """Load all expansion specifications."""
    specifications = loader.load_all()

    if isinstance(specifications, Mapping):
        values = list(specifications.values())
    elif isinstance(specifications, Sequence) and not isinstance(
        specifications, (str, bytes)
    ):
        values = list(specifications)
    else:
        raise TypeError(
            "SpecificationLoader.load_all() must return a mapping "
            "or a sequence of specifications."
        )

    for specification in values:
        if not isinstance(specification, Mapping):
            raise ValueError("Loaded specifications must be JSON objects.")

    return values


def _output_path(output_dir: Path, name: str) -> Path:
    """Build an output path for an expansion."""
    if not name or Path(name).name != name:
        raise ValueError(f"Invalid expansion code: {name!r}")

    return output_dir / f"{name}.uvl"


def _write_feature_model(feature_model: Any, output_path: Path) -> None:
    """Serialize a feature model to UVL."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    UVLWriter(
        path=str(output_path),
        source_model=feature_model,
    ).transform()

    logger.info("Feature model written to %s", output_path)


def _merge_specifications(
    specifications: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Merge expansion specifications into a global specification."""
    if not specifications:
        raise ValueError("At least one specification is required.")

    merged = deepcopy(dict(specifications[0]))
    merged["expansion_code"] = "ALL_EXPANSIONS"
    merged["expansion_name"] = "All expansions"

    total_cards = merged.get("total_cards", 0)
    if not isinstance(total_cards, int):
        raise ValueError("total_cards must be an integer.")

    points = {
        point["name"]: point
        for point in merged.get("variation_points", [])
    }

    for specification in specifications[1:]:
        cards = specification.get("total_cards", 0)

        if not isinstance(cards, int):
            raise ValueError("total_cards must be an integer.")

        total_cards += cards

        for source_point in specification.get("variation_points", []):
            name = source_point["name"]

            if name not in points:
                copied = deepcopy(source_point)
                merged.setdefault("variation_points", []).append(copied)
                points[name] = copied
            else:
                _merge_variation_point(points[name], source_point)

    merged["total_cards"] = total_cards
    return merged


def _merge_variation_point(
    target: dict[str, Any],
    source: Mapping[str, Any],
) -> None:
    """Merge one variation point recursively."""
    target["total_observations"] = (
        target.get("total_observations", 0)
        + source.get("total_observations", 0)
    )
    target["missing_observations"] = (
        target.get("missing_observations", 0)
        + source.get("missing_observations", 0)
    )

    target["source_attributes"] = list(
        dict.fromkeys(
            [
                *target.get("source_attributes", []),
                *source.get("source_attributes", []),
            ]
        )
    )

    target_variants = {
        variant["name"]: variant
        for variant in target.get("variants", [])
    }

    for source_variant in source.get("variants", []):
        name = source_variant["name"]

        if name not in target_variants:
            copied = deepcopy(source_variant)
            target.setdefault("variants", []).append(copied)
            target_variants[name] = copied
            continue

        target_variant = target_variants[name]

        # Keep the highest occurrence count to avoid inflating counts
        # when the same Oracle card appears in multiple expansions.
        target_variant["occurrences"] = max(
            target_variant.get("occurrences", 0),
            source_variant.get("occurrences", 0),
        )

        target_variant["examples"] = list(
            dict.fromkeys(
                [
                    *target_variant.get("examples", []),
                    *source_variant.get("examples", []),
                ]
            )
        )

        _merge_child_points(
            target_variant,
            source_variant,
        )

    _merge_child_points(target, source)
    _merge_statistics(target, source)


def _merge_child_points(
    target: dict[str, Any],
    source: Mapping[str, Any],
) -> None:
    """Merge nested variation points by name."""
    target_children = target.setdefault("child_points", [])
    source_children = source.get("child_points", [])

    if not isinstance(source_children, list):
        return

    children_by_name = {
        child["name"]: child
        for child in target_children
    }

    for source_child in source_children:
        name = source_child["name"]

        if name not in children_by_name:
            copied = deepcopy(source_child)
            target_children.append(copied)
            children_by_name[name] = copied
        else:
            _merge_variation_point(
                children_by_name[name],
                source_child,
            )


def _merge_statistics(
    target: dict[str, Any],
    source: Mapping[str, Any],
) -> None:
    """Merge numeric, special-value and cardinality statistics."""
    target_statistics = target.setdefault("statistics", {})
    source_statistics = source.get("statistics", {})

    if not isinstance(source_statistics, Mapping):
        return

    for key, operation in (
        ("numeric_minimum", min),
        ("numeric_maximum", max),
        ("minimum_cardinality", min),
        ("maximum_cardinality", max),
    ):
        source_value = source_statistics.get(key)

        if source_value is None:
            continue

        target_value = target_statistics.get(key)

        if target_value is None:
            target_statistics[key] = source_value
        else:
            target_statistics[key] = operation(
                target_value,
                source_value,
            )

    target_special = target_statistics.setdefault("special_values", [])
    source_special = source_statistics.get("special_values", [])

    if isinstance(source_special, list):
        target_statistics["special_values"] = list(
            dict.fromkeys([*target_special, *source_special])
        )


def main() -> None:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description="Build MTG feature models from variability specifications."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.toml"),
        help="Pipeline configuration file.",
    )
    parser.add_argument(
        "--expansion",
        type=str,
        default=None,
        help="Build only the specified expansion.",
    )

    args = parser.parse_args()

    run_phase3(
        config_path=args.config,
        expansion_code=args.expansion,
    )


if __name__ == "__main__":
    main()
