from pathlib import Path

from mtg_variability.config import PipelineConfig

config = PipelineConfig.from_toml(Path("config.toml"))

print(config.data_dir)
print(config.products_dir)
print(config.expansions_file)
print(config.taxonomy_path)
print(config.uvl_output_dir)