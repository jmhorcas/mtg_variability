from abc import ABC, abstractmethod

from flamapy.metamodels.fm_metamodel.models import FeatureModel


class BaseVariationStrategy(ABC):
    """Interface (Strategy Pattern) for injecting any variation point."""
    
    @abstractmethod
    def inject(self, model: FeatureModel, parent_feature_name: str, variants: list[str]) -> None:
        pass