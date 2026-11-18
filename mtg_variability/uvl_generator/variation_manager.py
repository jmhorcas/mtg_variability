from flamapy.metamodels.fm_metamodel.models import FeatureModel

from .strategies import BaseVariationStrategy


class VariationManager:
    """Manager class (Registry Pattern) for coordinating the injections."""
    
    def __init__(self, model: FeatureModel):
        self.model = model
        self._strategies: dict[str, tuple[BaseVariationStrategy, str]] = {}  # Maps feature names to their corresponding strategies and the property name (in the variant file) to be injected

    def register_strategy(self, feature_name: str, strategy: BaseVariationStrategy, data_key: str | None = None) -> None:
        """Register a strategy for a feature in the model, allowing to specify a different data key for lookup in the variant dictionary (e.g., 'power' -> 'Power')."""
        key_to_lookup = data_key if data_key is not None else feature_name
        self._strategies[feature_name] = (strategy, key_to_lookup)

    def apply_variations(self, expansion_data: dict[str, list[str]]) -> FeatureModel:
        for feature_name, (strategy, data_key) in self._strategies.items():
            # Look-up using the data key (e.g., 'power'), but inject into the feature name (e.g., 'Power')
            variants = expansion_data.get(data_key, [])
            if variants:
                strategy.inject(self.model, feature_name, variants)
        return self.model