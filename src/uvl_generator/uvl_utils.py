from typing import Optional, Iterable, Any

from flamapy.core.models.ast import AST, ASTOperation, Node, NodeType
from flamapy.metamodels.fm_metamodel.models import Constraint



def apply_constraints(fm: FeatureModel, feature_variations: dict[str, set[int]]) -> None:
    """Apply range constraints to the feature model based on variations.

    fm: The feature model to which constraints will be applied.
    feature_variations: A dictionary mapping feature names to sets of unique numerical values.
    """
    for feature_name, values in feature_variations.items():
        constraint = create_range_constraint(feature_name, values)
        if constraint:
            fm.get_constraints().append(constraint)
            feature_obj = fm.get_feature_by_name(feature_name)
            if feature_obj:
                feature_obj.constraints_attributes.append(constraint)


def create_range_constraint(identifier: str, values: Iterable[int], constraint_name: Optional[str] = None) -> Optional[Constraint]:
    """Create a minimum and maximum range constraint for any identifier based on a set or list of values.

    identifier: The name of the feature or variable for which the constraint is being created.
    values: A set or list of numerical values from which the minimum and maximum will be derived.
    constraint_name: Optional name for the constraint. If not provided, a default name will be generated based on the identifier.
    Returns a Constraint object representing the range constraint, or None if values is empty.
    """
    if not values:
        return None
    min_val = min(values)
    max_val = max(values)
    name = constraint_name or f"c_{identifier.lower().replace(' ', '_')}_range"
    # Create nodes for minimum and maximum bounds
    node_ge = Node(
        data=ASTOperation.GREATER_EQUALS,
        left=Node(data=identifier, node_type=NodeType.FEATURE),
        right=Node(data=min_val, node_type=NodeType.LITERAL)
    )
    node_le = Node(
        data=ASTOperation.LOWER_EQUALS,
        left=Node(data=identifier, node_type=NodeType.FEATURE),
        right=Node(data=max_val, node_type=NodeType.LITERAL)
    )
    # Combine bounds with an AND operator: identifier >= min_val && identifier <= max_val
    root_node = Node(
        data=ASTOperation.AND,
        left=node_ge,
        right=node_le
    )
    return Constraint(name=name, ast=AST(root_node))


def add_features_group(fm: FeatureModel, parent_name: str, children_names: list[str], card_min: Optional[int] = None, card_max: Optional[int] = None) -> None:
    """Add a child feature group under a parent feature with customizable cardinalities.
    
    If cardinalities are not provided, defaults to mandatory (1, 1) for 1 child, 
    or OR group (1, len) for multiple children.
    """
    if not children_names:
        return
    
    parent_feature = fm.get_feature_by_name(parent_name)
    if not parent_feature:
        raise ValueError(f"Parent feature '{parent_name}' not found in the feature model.")
    
    child_features = []
    for name in children_names:
        child = fm.get_feature_by_name(name)
        if not child:
            child = Feature(name=name, parent=parent_feature)
        child_features.append(child)
    num_children = len(child_features)
    
    # Derive default cardinalities if not specified
    if card_min is None or card_max is None:
        if num_children == 1:
            card_min, card_max = 1, 1  # Mandatory relation
        else:
            card_min, card_max = 1, num_children  # OR group relation
            
    relation = Relation(
        parent=parent_feature, 
        children=child_features, 
        card_min=card_min, 
        card_max=card_max
    )
    parent_feature.add_relation(relation)


# def apply_numerical_bounds(fm: FeatureModel, expansion_variants: dict[str, set[int]]) -> None:
#     """Apply numerical bounds to the feature model based on expansion variants."""
#     for feature_name, values in expansion_variants.items():
#         if values:
#             constraint = create_range_constraint(feature_name, values)
#             if constraint:
#                 fm.get_constraints().append(constraint)
#                 feature_obj = fm.get_feature_by_name(feature_name)
#                 if feature_obj:
#                     feature_obj.constraints_attributes.append(constraint)