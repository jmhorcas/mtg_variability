# src/uvl_generator/pipeline.py
import ast
import logging
from pathlib import Path
from typing import Any

from flamapy.metamodels.fm_metamodel.transformations.uvl_reader import UVLReader
from flamapy.metamodels.fm_metamodel.transformations.uvl_writer import UVLWriter

from .variation_manager import VariationManager
from .strategies import (
    AlternativeListInjectionStrategy, 
    OrListInjectionStrategy,
    OptionalListInjectionStrategy,
    CreatureStatInjectionStrategy
)

logger = logging.getLogger("uvl_generation")


class UVLGenerationPipeline:
    """Phase 3: Reads the local .dat variant files and generates UVL models using Flamapy."""

    def __init__(
        self, 
        data_dir: Path = Path("data"), 
        output_dir: Path = Path("uvl_models/generated"), 
        template_path: Path = Path("uvl_models/templates/base.uvl")
    ):
        self.variants_dir = data_dir / "variants"
        self.output_dir = output_dir
        self.template_path = template_path
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _load_variants_dat(self, path: Path) -> dict[str, list[Any]]:
        """Reads a _variants.dat file and deserializes it back to a Python dictionary."""
        variants = {}
        if not path.exists():
            return variants
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            prop, _, raw_values = line.partition(": ")
            try:
                #ast.literal_eval convert the string representation of the list into a real Python list
                variants[prop] = ast.literal_eval(raw_values)
            except (ValueError, SyntaxError):
                variants[prop] = []
        return variants

    def run(self) -> None:
        logger.info("🧬 Phase 3: Starting UVL model generation with Flamapy...")
        
        if not self.template_path.exists():
            logger.error("❌ Base template not found at: %s", self.template_path)
            return

        variant_files = sorted(list(self.variants_dir.glob("*_variants.dat")))
        total = len(variant_files)

        for i, dat_path in enumerate(variant_files, start=1):
            # Omit the global consolidated file if it exists
            if dat_path.name == "all_expansions_variants.dat":
                continue

            # 1. Load a fresh copy of the base template for each expansion independently
            base_model = UVLReader(str(self.template_path)).transform()

            # 2. Read the specific variants for this expansion from its local .dat file
            expansion_variants = self._load_variants_dat(dat_path)

            # 3. Configure the variation manager (Registry Pattern) and register strategies
            manager = VariationManager(base_model)
            manager.register_strategy("Rarity", AlternativeListInjectionStrategy(), data_key="rarity")
            manager.register_strategy("Supertypes", OrListInjectionStrategy(), data_key="supertypes")
            manager.register_strategy("Type", OrListInjectionStrategy(), data_key="types")
            for card_type in expansion_variants.get("types", []):
                card_subtypes_key = f"{card_type} Subtypes"
                if card_subtypes_key in expansion_variants and expansion_variants[card_subtypes_key]:
                    expansion_variants.setdefault(f"{card_type}", [card_subtypes_key])
                    manager.register_strategy(card_type, OptionalListInjectionStrategy(), data_key=f"{card_type}")
                    manager.register_strategy(card_subtypes_key, OrListInjectionStrategy(), data_key=card_subtypes_key)
            manager.register_strategy("Power", CreatureStatInjectionStrategy("Power"), data_key="power")
            manager.register_strategy("Toughness", CreatureStatInjectionStrategy("Toughness"), data_key="toughness")
            
            # 4. Apply the polymorphic injection to the Flamapy metamodel
            final_model = manager.apply_variations(expansion_variants)

            # 5. Export the resulting model to a clean physical .uvl file
            output_filename = dat_path.name.replace("_variants.dat", ".uvl")
            output_uvl_path = self.output_dir / output_filename
            
            uvl_writer = UVLWriter(str(output_uvl_path), final_model)
            uvl_writer.set_compact_relations(True)
            uvl_writer.transform()
            logger.info("✨ [%d/%d] Generated: %s", i, total, output_uvl_path.name)

            raise Exception("Test Exception")  # For testing purposes, remove this line in production

        logger.info("🏁 Phase 3 completed successfully. All UVL models are in %s", self.output_dir)