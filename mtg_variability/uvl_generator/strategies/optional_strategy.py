from flamapy.metamodels.fm_metamodel.models import Feature, Relation, FeatureModel

from .base_strategy import BaseVariationStrategy


class OptionalListInjectionStrategy(BaseVariationStrategy):
    """Generic strategy for injecting optional variation points (e.g., Artifact Supertypes)."""
    
    def inject(self, model: FeatureModel, parent_feature_name: str, variants: list[str]) -> None:
        parent_feature = model.get_feature_by_name(parent_feature_name)
        if not parent_feature:
            raise ValueError(f"Feature '{parent_feature_name}' not found in the base model.")
        
        #clean_variants = sorted(list(set(str(v) for v in variants)))
        child_features = [Feature(name=var) for var in variants]
        
        relation = Relation(
            parent=parent_feature,
            children=child_features,
            card_min=0,
            card_max=len(child_features)
        )
        parent_feature.add_relation(relation)
        
        for child in child_features:
            child.parent = parent_feature