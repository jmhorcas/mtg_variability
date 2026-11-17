from flamapy.metamodels.fm_metamodel.models import FeatureModel

from uvl_generator.strategies import BaseVariationStrategy


class VariationManager:
    """Manager class (Registry Pattern) for coordinating the injections."""
    
    def __init__(self, model: FeatureModel):
        self.model = model
        self._strategies: dict[str, BaseVariationStrategy] = {}

    def register_strategy(self, feature_name: str, strategy: BaseVariationStrategy) -> None:
        self._strategies[feature_name] = strategy

    def apply_variations(self, expansion_data: dict[str, list[str]]) -> FeatureModel:
        for feature_name, variants in expansion_data.items():
            if feature_name in self._strategies:
                strategy = self._strategies[feature_name]
                strategy.inject(self.model, feature_name, variants)
        return self.model