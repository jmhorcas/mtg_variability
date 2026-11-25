
"""Tests for direct Flamapy feature model construction."""

import pytest

from flamapy.metamodels.fm_metamodel.models.feature_model import FeatureModel

from mtg_variability.feature_model.builder import FeatureModelBuilder


@pytest.fixture
def builder():
    return FeatureModelBuilder()


@pytest.fixture
def specification():
    return {
        "schema_version": 1,
        "expansion_code": "TST",
        "expansion_name": "Test Expansion",
        "total_cards": 4,
        "variation_points": [
            {
                "name": "layout",
                "category": "functional",
                "child_points": [],
                "missing_observations": 0,
                "variants": [
                    {"name": "normal", "occurrences": 3},
                    {"name": "transform", "occurrences": 1},
                ],
            },
            {
                "name": "rarity",
                "category": "collection",
                "child_points": [],
                "missing_observations": 0,
                "variants": [
                    {"name": "common", "occurrences": 2},
                    {"name": "rare", "occurrences": 2},
                ],
            },
            {
                "name": "watermark",
                "category": "presentation",
                "child_points": [],
                "missing_observations": 2,
                "variants": [
                    {"name": "set_a", "occurrences": 1},
                    {"name": "set_b", "occurrences": 1},
                ],
            },
        ],
    }


def test_build_returns_flamapy_feature_model(builder, specification):
    model = builder.build(specification)

    assert isinstance(model, FeatureModel)
    assert model.root.name == "MTG"


def test_build_creates_mandatory_category_features(builder, specification):
    model = builder.build(specification)

    root = model.root
    categories = {
        relation.children[0].name: relation
        for relation in root.relations
    }

    assert set(categories) == {
        "functional",
        "collection",
        "presentation",
    }

    for relation in categories.values():
        assert relation.card_min == 1
        assert relation.card_max == 1


def test_categorical_variation_point_is_mandatory_without_missing_values(
    builder,
    specification,
):
    model = builder.build(specification)

    functional = model.get_feature_by_name("functional")
    relation = next(
        relation
        for relation in functional.relations
        if relation.children[0].name == "functional_layout"
    )

    assert relation.card_min == 1
    assert relation.card_max == 1


def test_categorical_variation_point_is_optional_with_missing_values(
    builder,
    specification,
):
    model = builder.build(specification)

    presentation = model.get_feature_by_name("presentation")
    relation = next(
        relation
        for relation in presentation.relations
        if relation.children[0].name == "presentation_watermark"
    )

    assert relation.card_min == 0
    assert relation.card_max == 1


def test_categorical_variants_form_an_alternative_group(
    builder,
    specification,
):
    model = builder.build(specification)

    layout = model.get_feature_by_name("functional_layout")

    assert layout is not None
    assert len(layout.relations) == 1

    relation = layout.relations[0]

    assert relation.card_min == 1
    assert relation.card_max == 1
    assert {
        feature.name for feature in relation.children
    } == {
        "functional_layout_normal",
        "functional_layout_transform",
    }


def test_all_variation_points_are_attached_to_their_categories(
    builder,
    specification,
):
    model = builder.build(specification)

    assert model.get_feature_by_name("functional_layout") is not None
    assert model.get_feature_by_name("collection_rarity") is not None
    assert model.get_feature_by_name("presentation_watermark") is not None

    assert (
        model.get_feature_by_name("functional_layout").parent.name
        == "functional"
    )
    assert (
        model.get_feature_by_name("collection_rarity").parent.name
        == "collection"
    )
    assert (
        model.get_feature_by_name("presentation_watermark").parent.name
        == "presentation"
    )


def test_feature_names_are_normalized(builder):
    name = builder._feature_name("Functional", "Power / Toughness")

    assert name == "functional_power_toughness"


def test_feature_names_start_with_a_letter(builder):
    name = builder._feature_name("Functional", "123 value")

    assert name == "functional_123_value"


def test_rejects_unknown_variability_category(builder, specification):
    specification["variation_points"][0]["category"] = "unknown"

    with pytest.raises(ValueError, match="Unsupported variability category"):
        builder.build(specification)


def test_rejects_categorical_variation_point_without_variants(
    builder,
    specification,
):
    specification["variation_points"][0]["variants"] = []

    with pytest.raises(ValueError, match="has no variants"):
        builder.build(specification)


@pytest.mark.parametrize("point_name", ["colors", "color_identity"])
def test_multivalue_point_creates_optional_value_features(
    builder,
    specification,
    point_name,
):
    specification["variation_points"] = [
        {
            "name": point_name,
            "category": "functional",
            "child_points": [],
            "missing_observations": 0,
            "total_observations": 4,
            "statistics": {
                "minimum_cardinality": 1,
                "maximum_cardinality": 2,
            },
            "variants": [
                {"name": "W", "occurrences": 2},
                {"name": "U", "occurrences": 2},
                {"name": "B", "occurrences": 1},
                {"name": "R", "occurrences": 1},
                {"name": "G", "occurrences": 2},
            ],
        }
    ]

    model = builder.build(specification)
    point = model.get_feature_by_name(f"functional_{point_name}")

    assert point is not None
    assert len(point.relations) == 1

    relation = point.relations[0]

    assert relation.card_min == 1
    assert relation.card_max == 2
    assert {
        feature.name for feature in relation.children
    } == {
        f"functional_{point_name}_{color}"
        for color in ("w", "u", "b", "r", "g")
    }


def test_multivalue_point_preserves_zero_cardinality(
    builder,
    specification,
):
    specification["variation_points"] = [
        {
            "name": "colors",
            "category": "functional",
            "child_points": [],
            "missing_observations": 0,
            "total_observations": 4,
            "statistics": {
                "minimum_cardinality": 0,
                "maximum_cardinality": 2,
            },
            "variants": [
                {"name": "W", "occurrences": 2},
                {"name": "U", "occurrences": 2},
                {"name": "B", "occurrences": 1},
            ],
        }
    ]

    model = builder.build(specification)
    point = model.get_feature_by_name("functional_colors")
    relation = point.relations[0]

    assert relation.card_min == 0
    assert relation.card_max == 2


def test_multivalue_point_can_be_optional_when_observations_are_missing(
    builder,
    specification,
):
    specification["variation_points"] = [
        {
            "name": "colors",
            "category": "functional",
            "child_points": [],
            "missing_observations": 1,
            "total_observations": 4,
            "statistics": {
                "minimum_cardinality": 1,
                "maximum_cardinality": 2,
            },
            "variants": [
                {"name": "W", "occurrences": 2},
                {"name": "U", "occurrences": 2},
            ],
        }
    ]

    model = builder.build(specification)
    functional = model.get_feature_by_name("functional")

    relation = next(
        relation
        for relation in functional.relations
        if relation.children[0].name == "functional_colors"
    )

    assert relation.card_min == 0
    assert relation.card_max == 1


@pytest.mark.parametrize(
    ("minimum", "maximum"),
    [
        (-1, 2),
        (2, 1),
        (0, 4),
        (True, 2),
    ],
)
def test_multivalue_point_rejects_invalid_cardinality(
    builder,
    specification,
    minimum,
    maximum,
):
    specification["variation_points"] = [
        {
            "name": "colors",
            "category": "functional",
            "child_points": [],
            "missing_observations": 0,
            "total_observations": 4,
            "statistics": {
                "minimum_cardinality": minimum,
                "maximum_cardinality": maximum,
            },
            "variants": [
                {"name": "W", "occurrences": 2},
                {"name": "U", "occurrences": 2},
                {"name": "B", "occurrences": 1},
            ],
        }
    ]

    with pytest.raises(ValueError, match="Invalid cardinality bounds"):
        builder.build(specification)


def test_multivalue_point_rejects_missing_cardinality_statistics(
    builder,
    specification,
):
    specification["variation_points"] = [
        {
            "name": "colors",
            "category": "functional",
            "child_points": [],
            "missing_observations": 0,
            "total_observations": 4,
            "statistics": {
                "minimum_cardinality": 1,
            },
            "variants": [
                {"name": "W", "occurrences": 2},
                {"name": "U", "occurrences": 2},
            ],
        }
    ]

    # An incomplete statistics object must not be silently interpreted
    # as a categorical variation point.
    with pytest.raises(
        ValueError,
        match="Missing cardinality statistics",
    ):
        builder.build(specification)



def test_builds_type_system_hierarchy(builder, specification):
    specification["variation_points"] = [
        {
            "name": "type",
            "category": "functional",
            "missing_observations": 0,
            "variants": [],
            "statistics": None,
            "child_points": [
                {
                    "name": "supertypes",
                    "missing_observations": 0,
                    "statistics": {
                        "minimum_cardinality": 0,
                        "maximum_cardinality": 2,
                    },
                    "variants": [
                        {"name": "Legendary", "occurrences": 2},
                        {"name": "Basic", "occurrences": 1},
                    ],
                    "child_points": [],
                },
                {
                    "name": "card_types",
                    "missing_observations": 0,
                    "statistics": {
                        "minimum_cardinality": 1,
                        "maximum_cardinality": 2,
                    },
                    "variants": [
                        {"name": "Artifact", "occurrences": 2},
                        {"name": "Creature", "occurrences": 2},
                        {"name": "Land", "occurrences": 1},
                    ],
                    "child_points": [],
                },
                {
                    "name": "subtypes",
                    "missing_observations": 0,
                    "variants": [],
                    "statistics": None,
                    "child_points": [
                        {
                            "name": "subtypes:artifact",
                            "missing_observations": 0,
                            "statistics": {
                                "minimum_cardinality": 0,
                                "maximum_cardinality": 2,
                            },
                            "variants": [
                                {"name": "Equipment", "occurrences": 2},
                                {"name": "Vehicle", "occurrences": 1},
                            ],
                            "child_points": [],
                        },
                        {
                            "name": "subtypes:creature",
                            "missing_observations": 0,
                            "statistics": {
                                "minimum_cardinality": 0,
                                "maximum_cardinality": 2,
                            },
                            "variants": [
                                {"name": "Human", "occurrences": 2},
                                {"name": "Wizard", "occurrences": 1},
                            ],
                            "child_points": [],
                        },
                    ],
                },
            ],
        }
    ]

    model = builder.build(specification)

    assert model.get_feature_by_name("functional_type") is not None
    assert model.get_feature_by_name("functional_type_supertypes") is not None
    assert model.get_feature_by_name("functional_type_card_types") is not None
    assert model.get_feature_by_name("functional_type_subtypes") is not None

    assert (
        model.get_feature_by_name("functional_type_supertypes").parent.name
        == "functional_type"
    )
    assert (
        model.get_feature_by_name("functional_type_card_types").parent.name
        == "functional_type"
    )
    assert (
        model.get_feature_by_name("functional_type_subtypes").parent.name
        == "functional_type"
    )

    assert (
        model.get_feature_by_name(
            "functional_type_subtypes_artifact"
        ).parent.name
        == "functional_type_subtypes"
    )


def test_type_system_preserves_multivalue_cardinalities(
    builder,
    specification,
):
    specification["variation_points"] = [
        {
            "name": "type",
            "category": "functional",
            "missing_observations": 0,
            "variants": [],
            "statistics": None,
            "child_points": [
                {
                    "name": "card_types",
                    "missing_observations": 0,
                    "statistics": {
                        "minimum_cardinality": 1,
                        "maximum_cardinality": 2,
                    },
                    "variants": [
                        {"name": "Artifact", "occurrences": 2},
                        {"name": "Creature", "occurrences": 2},
                        {"name": "Land", "occurrences": 1},
                    ],
                    "child_points": [],
                }
            ],
        }
    ]

    model = builder.build(specification)
    card_types = model.get_feature_by_name(
        "functional_type_card_types"
    )

    relation = card_types.relations[0]

    assert relation.card_min == 1
    assert relation.card_max == 2

    assert {
        feature.name for feature in relation.children
    } == {
        "functional_type_card_types_artifact",
        "functional_type_card_types_creature",
        "functional_type_card_types_land",
    }


def test_subtype_categories_are_independent_groups(
    builder,
    specification,
):
    specification["variation_points"] = [
        {
            "name": "type",
            "category": "functional",
            "missing_observations": 0,
            "variants": [],
            "statistics": None,
            "child_points": [
                {
                    "name": "subtypes",
                    "missing_observations": 0,
                    "variants": [],
                    "statistics": None,
                    "child_points": [
                        {
                            "name": "subtypes:artifact",
                            "missing_observations": 0,
                            "statistics": {
                                "minimum_cardinality": 0,
                                "maximum_cardinality": 1,
                            },
                            "variants": [
                                {"name": "Equipment", "occurrences": 2},
                            ],
                            "child_points": [],
                        },
                        {
                            "name": "subtypes:creature",
                            "missing_observations": 0,
                            "statistics": {
                                "minimum_cardinality": 0,
                                "maximum_cardinality": 2,
                            },
                            "variants": [
                                {"name": "Human", "occurrences": 2},
                                {"name": "Wizard", "occurrences": 1},
                            ],
                            "child_points": [],
                        },
                    ],
                }
            ],
        }
    ]

    model = builder.build(specification)

    artifact = model.get_feature_by_name(
        "functional_type_subtypes_artifact"
    )
    creature = model.get_feature_by_name(
        "functional_type_subtypes_creature"
    )

    assert artifact is not None
    assert creature is not None

    assert artifact.parent.name == "functional_type_subtypes"
    assert creature.parent.name == "functional_type_subtypes"

    assert artifact.relations[0].card_min == 0
    assert artifact.relations[0].card_max == 1

    assert creature.relations[0].card_min == 0
    assert creature.relations[0].card_max == 2


def test_rejects_hierarchical_point_with_variants(
    builder,
    specification,
):
    specification["variation_points"] = [
        {
            "name": "type",
            "category": "functional",
            "missing_observations": 0,
            "variants": [
                {"name": "Creature", "occurrences": 2},
            ],
            "child_points": [
                {
                    "name": "card_types",
                    "missing_observations": 0,
                    "variants": [
                        {"name": "Creature", "occurrences": 2},
                    ],
                    "child_points": [],
                }
            ],
        }
    ]

    with pytest.raises(
        ValueError,
        match="cannot contain variants",
    ):
        builder.build(specification)
