from flamapy.metamodels.fm_metamodel.models import Feature, Relation, FeatureModel

from .base_strategy import BaseVariationStrategy
from uvl_generator import uvl_utils


class CreatureStatInjectionStrategy(BaseVariationStrategy):
    """Generic strategy for injecting creature statistics (Power or Toughness) into the feature model."""
    
    def __init__(self, stat_name: str):
        self.stat_name = stat_name
    
    def inject(self, model: FeatureModel, parent_feature_name: str, variants: list[str]) -> None:
        parent_feature = model.get_feature_by_name(parent_feature_name)
        if not parent_feature:
            raise ValueError(f"Feature '{parent_feature_name}' not found in the base model.")
        
        value_feat_name = f"{self.stat_name} value"
        modifiers_feat_name = f"{self.stat_name} modifiers"
        sign_feat_name = f"{self.stat_name} sign"
        c_star_feat_name = f"{self.stat_name} Complex Star"
        
        power_value_feat = Feature(value_feat_name, feature_type=FeatureType.INTEGER)
        
        special_children = []
        for v in variants:
            v_str = str(v)
            if v_str == '∞':
                special_children.append(Feature(f"{self.stat_name} Infinity"))
            elif v_str == '?':
                special_children.append(Feature(f"{self.stat_name} Unknown"))
            elif v_str == '*':
                special_children.append(Feature(f"{self.stat_name} Star"))
            elif v_str == '*²':
                special_children.append(Feature(f"{self.stat_name} Complex Star Squared"))

        has_numeric = any(not str(v).startswith('*') and v not in ['?', '∞'] for v in variants)
        alternative_children = []
        if has_numeric:
            alternative_children.append(power_value_feat)
            
            modifiers_feat = Feature(modifiers_feat_name, is_abstract=True, parent=power_value_feat)
            mod_relation = Relation(
                parent=power_value_feat,
                children=[modifiers_feat],
                card_min=0,
                card_max=1
            )
            power_value_feat.add_relation(mod_relation)

            mod_alternatives = []
            has_signs = any('+' in str(v) or '-' in str(v) for v in variants if '*' not in str(v))
            if has_signs:
                sign_feat = Feature(sign_feat_name, is_abstract=True, parent=modifiers_feat)
                plus_name = f"{self.stat_name} modifier Plus"
                minus_name = f"{self.stat_name} modifier Minus"
                uvl_utils.add_features_group(model, sign_feat.name, [plus_name, minus_name], card_min=1, card_max=1)
                mod_alternatives.append(sign_feat)

            has_complex_stars = any('*' in str(v) and v != '*' and v != '*²' for v in variants)
            if has_complex_stars:
                c_star_feat = Feature(c_star_feat_name, is_abstract=True, parent=modifiers_feat)
                c_plus_name = f"{self.stat_name} Complex Star Plus"
                c_minus_name = f"{self.stat_name} Complex Star Minus"
                uvl_utils.add_features_group(model, c_star_feat.name, [c_plus_name, c_minus_name], card_min=1, card_max=1)
                mod_alternatives.append(c_star_feat)

            if '.5' in [str(v) for v in variants]:
                half_feat = Feature(f"{self.stat_name} half", parent=modifiers_feat)
                mod_alternatives.append(half_feat)

            if mod_alternatives:
                mod_rel = Relation(parent=modifiers_feat, children=mod_alternatives, card_min=1, card_max=1)
                modifiers_feat.add_relation(mod_rel)

            # Extract numerical values from variants for applying create_range_constraint
            numeric_vals = []
            for v in variants:
                try:
                    num = int(v)
                    numeric_vals.append(num)
                except ValueError:
                    pass
            
            if numeric_vals:
                constraint = create_range_constraint(value_feat_name, numeric_vals, constraint_name=f"c_{self.stat_name.lower()}_range")
                if constraint:
                    fm.get_constraints().append(constraint)
                    power_value_feat.constraints_attributes.append(constraint)

        alternative_children.extend(special_children)
        stat_relation = Relation(parent=parent_feature, children=alternative_children, card_min=1, card_max=1)
        parent_feature.add_relation(stat_relation)
