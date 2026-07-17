"""Tests for default-backed nested ``Fn::ForEach`` resolution."""

from cfnlint.template import Template
from cfnlint.template.transforms._language_extensions import (
    _ForEachCollection,
    _ForEachValue,
    language_extension,
)


def _template(
    *,
    selector_map="Selectors",
    collection_map="Collections",
    outer_loop="Stages",
    inner_loop="Services",
    resource_type="AWS::S3::Bucket",
):
    return {
        "Transform": "AWS::LanguageExtensions",
        "Mappings": {
            selector_map: {"Development": {"Present": "Unused"}},
            collection_map: {"Fallback": {"Values": ["One", "Two"]}},
        },
        "Resources": {
            f"Fn::ForEach::{outer_loop}": [
                "Stage",
                ["Development"],
                {
                    f"Fn::ForEach::{inner_loop}": [
                        "Service",
                        {
                            "Fn::FindInMap": [
                                collection_map,
                                {
                                    "Fn::FindInMap": [
                                        selector_map,
                                        {"Ref": "Stage"},
                                        "Absent",
                                        {"DefaultValue": "Fallback"},
                                    ]
                                },
                                "Values",
                            ]
                        },
                        {
                            "${Stage}${Service}Resource": {
                                "Type": resource_type,
                            }
                        },
                    ]
                },
            ]
        },
    }


def _cfn(template):
    return Template(filename="", template=template, regions=["us-east-1"])


def test_cfnlint_001_missing_mapping_key_uses_declared_default():
    """GUID: CFNLINT-001 - an absent key resolves to DefaultValue."""
    template = _template()
    lookup = _ForEachValue.create(
        {
            "Fn::FindInMap": [
                "Selectors",
                "Development",
                "Absent",
                {"DefaultValue": "Fallback"},
            ]
        }
    )

    assert lookup.value(_cfn(template)) == "Fallback"


def test_cfnlint_002_default_becomes_enclosing_find_in_map_key():
    """GUID: CFNLINT-002 - the resolved default becomes the enclosing key."""
    template = _template()
    nested_lookup = _ForEachValue.create(
        template["Resources"]["Fn::ForEach::Stages"][2][
            "Fn::ForEach::Services"
        ][1]
    )

    assert nested_lookup.value(_cfn(template), {"Stage": "Development"}) == [
        "One",
        "Two",
    ]


def test_cfnlint_003_enclosing_collection_is_consumed_by_nested_for_each():
    """GUID: CFNLINT-003 - the enclosing collection feeds the nested loop."""
    template = _template()
    collection_expression = template["Resources"]["Fn::ForEach::Stages"][2][
        "Fn::ForEach::Services"
    ][1]
    collection = _ForEachCollection(collection_expression)

    assert list(
        collection.values(_cfn(template), {}, {"Stage": "Development"})
    ) == ["One", "Two"]


def test_cfnlint_004_valid_default_backed_nested_loops_emit_no_errors():
    """GUID: CFNLINT-004 - valid nested loops emit no transform errors."""
    matches, transformed = language_extension(_cfn(_template()))

    assert matches == []
    assert set(transformed["Resources"]) == {
        "DevelopmentOneResource",
        "DevelopmentTwoResource",
    }


def test_cfnlint_009_equivalent_names_loops_and_resource_types_transform():
    """GUID: CFNLINT-009 - equivalent valid intrinsic patterns transform."""
    template = _template(
        selector_map="RoutingTable",
        collection_map="QueueGroups",
        outer_loop="Environments",
        inner_loop="Queues",
        resource_type="AWS::SQS::Queue",
    )

    matches, transformed = language_extension(_cfn(template))

    assert matches == []
    assert transformed["Resources"] == {
        "DevelopmentOneResource": {"Type": "AWS::SQS::Queue"},
        "DevelopmentTwoResource": {"Type": "AWS::SQS::Queue"},
    }
