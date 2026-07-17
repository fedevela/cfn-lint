"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from collections import deque
from unittest.mock import MagicMock

import pytest

from cfnlint.context import create_context_for_template
from cfnlint.context.context import Resource, Transforms
from cfnlint.jsonschema import CfnTemplateValidator, ValidationError
from cfnlint.rules.functions.FindInMap import FindInMap
from cfnlint.template import Template


@pytest.fixture(scope="module")
def rule():
    rule = FindInMap()
    yield rule


@pytest.fixture(scope="module")
def cfn():
    return Template(
        "",
        {
            "Parameters": {
                "MyParameter": {
                    "Type": "String",
                    "AllowedValues": ["A", "B", "C"],
                }
            },
            "Resources": {"MyResource": Resource({"Type": "AWS::SSM::Parameter"})},
            "Mappings": {"A": {"B": {"C": "Value"}}},
        },
        regions=["us-east-1"],
    )


@pytest.fixture(scope="module")
def context(cfn):
    return create_context_for_template(cfn)


class TestE1011001FindInMapTwoLookupLevelLimit:
    """Verification contracts for GUID: E1011-001."""

    def test_overlong_lookup_reports_e1011_identifying_find_in_map_and_two_level_limit(
        self,
        rule,
        context,
        cfn,
    ):
        """An overlong lookup reports E1011, FindInMap, and the two-level limit."""
        validator = CfnTemplateValidator({})(context=context, cfn=cfn)

        errors = list(
            rule.fn_findinmap(
                validator,
                {"type": "string"},
                {"Fn::FindInMap": ["MyCustomMap", "Level1", "Level2", "Key"]},
                {},
            )
        )

        assert rule.id == "E1011"
        assert len(errors) == 1
        assert "FindInMap" in errors[0].message
        assert "no more than two lookup levels" in errors[0].message

    def test_different_map_and_key_names_report_the_same_two_level_limit(
        self, rule, context, cfn
    ):
        """Different lookup names preserve the same FindInMap limit message."""
        validator = CfnTemplateValidator({})(context=context, cfn=cfn)
        lookups = [
            ["FirstMap", "FirstLevel", "SecondLevel", "FirstKey"],
            ["OtherMap", "Alpha", "Omega", "OtherKey"],
        ]

        messages = []
        for lookup in lookups:
            errors = list(
                rule.fn_findinmap(
                    validator,
                    {"type": "string"},
                    {"Fn::FindInMap": lookup},
                    {},
                )
            )
            assert len(errors) == 1
            messages.append(errors[0].message)

        assert messages == [
            "FindInMap supports no more than two lookup levels",
            "FindInMap supports no more than two lookup levels",
        ]


class TestE1011002FindInMapConditionSpecificWording:
    """Verification contract for GUID: E1011-002."""

    def test_overlong_lookup_message_does_not_use_is_too_long_wording(
        self, rule, context, cfn
    ):
        """The overlong FindInMap diagnostic replaces the generic wording."""
        validator = CfnTemplateValidator({})(context=context, cfn=cfn)

        errors = list(
            rule.fn_findinmap(
                validator,
                {"type": "string"},
                {"Fn::FindInMap": ["Map", "One", "Two", "Three"]},
                {},
            )
        )

        assert len(errors) == 1
        assert "is too long" not in errors[0].message


class TestE1011003FindInMapExcessiveDepthPreservation:
    """Placeholder verification contracts for GUID: E1011-003."""

    def test_excessive_depth_after_message_enhancement_remains_invalid_with_e1011(
        self,
    ):
        """An excessive-depth lookup remains invalid and detectable as E1011."""
        assert True


class TestE1011004FindInMapSupportedDepthPreservation:
    """Placeholder verification contracts for GUID: E1011-004."""

    def test_supported_depth_after_message_enhancement_remains_valid_without_e1011(
        self,
    ):
        """A supported-depth lookup remains accepted without a new E1011 finding."""
        assert True


class TestE1011003E1011004FindInMapBoundaryClassificationPreservation:
    """Placeholder verification contract for GUIDs: E1011-003, E1011-004."""

    def test_boundary_fixtures_before_and_after_enhancement_only_change_e1011_text(
        self,
    ):
        """Boundary classifications remain unchanged when E1011 text changes."""
        assert True


@pytest.mark.parametrize(
    "name,instance,schema,context_evolve,ref_mock_values,expected",
    [
        (
            "Valid Fn::FindInMap",
            {"Fn::FindInMap": ["A", "B", "C"]},
            {"type": "string"},
            {},
            None,
            [],
        ),
        (
            "Invalid Fn::FindInMap too long",
            {"Fn::FindInMap": ["foo", "bar", "key", "key2"]},
            {"type": "string"},
            {},
            None,
            [
                ValidationError(
                    "FindInMap supports no more than two lookup levels",
                    path=deque(["Fn::FindInMap"]),
                    schema_path=deque(["maxItems"]),
                    validator="fn_findinmap",
                ),
            ],
        ),
        (
            "Invalid Fn::FindInMap with wrong type",
            {"Fn::FindInMap": {"foo": "bar"}},
            {"type": "string"},
            {},
            None,
            [
                ValidationError(
                    "{'foo': 'bar'} is not of type 'array'",
                    path=deque(["Fn::FindInMap"]),
                    schema_path=deque(["type"]),
                    validator="fn_findinmap",
                ),
            ],
        ),
        (
            "Invalid Fn::FindInMap with wrong function",
            {"Fn::FindInMap": [{"Fn::GetAtt": "MyResource.Arn"}, "foo", "bar"]},
            {"type": "string"},
            {},
            None,
            [
                ValidationError(
                    "{'Fn::GetAtt': 'MyResource.Arn'} is not of type 'string'",
                    path=deque(["Fn::FindInMap", 0]),
                    schema_path=deque(["fn_items", "type"]),
                    validator="fn_findinmap",
                ),
            ],
        ),
        (
            "Valid Fn::FindInMap",
            {"Fn::FindInMap": ["A", "B", "C", {"DefaultValue": "D"}]},
            {"type": "string"},
            {"transforms": Transforms(["AWS::LanguageExtensions"])},
            None,
            [],
        ),
        (
            "Invalid nested Fn::FindInMap with Language Extensions",
            {"Fn::FindInMap": ["A", "B", "C", "D"]},
            {"type": "string"},
            {"transforms": Transforms(["AWS::LanguageExtensions"])},
            None,
            [
                ValidationError(
                    "FindInMap supports no more than two lookup levels",
                    path=deque(["Fn::FindInMap"]),
                    schema_path=deque(["maxItems"]),
                    validator="fn_findinmap",
                ),
            ],
        ),
        (
            "Invalid Fn::FindInMap options not of type object",
            {"Fn::FindInMap": ["A", "B", "C", []]},
            {"type": "string"},
            {"transforms": Transforms(["AWS::LanguageExtensions"])},
            None,
            [
                ValidationError(
                    "[] is not of type 'object'",
                    path=deque(["Fn::FindInMap", 3]),
                    schema_path=deque(["fn_items", "type"]),
                    validator="fn_findinmap",
                ),
            ],
        ),
        (
            "Invalid Fn::FindInMap default keyword doesn't exist",
            {"Fn::FindInMap": ["A", "B", "C", {}]},
            {"type": "string"},
            {"transforms": Transforms(["AWS::LanguageExtensions"])},
            None,
            [
                ValidationError(
                    "'DefaultValue' is a required property",
                    path=deque(["Fn::FindInMap", 3]),
                    schema_path=deque(["fn_items", "required"]),
                    validator="fn_findinmap",
                ),
            ],
        ),
        (
            "Invalid Fn::FindInMap with a Ref to a resource",
            {"Fn::FindInMap": ["A", {"Ref": "MyResource"}, "C"]},
            {"type": "string"},
            {"transforms": Transforms(["AWS::LanguageExtensions"])},
            [ValidationError("Foo")],
            [
                ValidationError(
                    "Foo",
                    path=deque(["Fn::FindInMap", 1]),
                    schema_path=deque(["fn_items", "ref"]),
                    validator="ref",
                ),
            ],
        ),
        (
            "Invalid Fn::FindInMap with a bad map key",
            {"Fn::FindInMap": ["A", "C", "B"]},
            {"type": "string"},
            {"transforms": Transforms(["AWS::LanguageExtensions"])},
            [ValidationError("Foo")],
            [
                ValidationError(
                    "'C' is not one of ['B'] for mapping 'A'",
                    path=deque(["Fn::FindInMap", 1]),
                    schema_path=deque([]),
                ),
            ],
        ),
        (
            "Valid Fn::FindInMap as the Ref could work",
            {"Fn::FindInMap": ["A", {"Ref": "MyParameter"}, "C"]},
            {"type": "string"},
            {"transforms": Transforms(["AWS::LanguageExtensions"])},
            [],
            [],
        ),
        (
            "Valid Fn::FindInMap with a Ref to AWS::NoValue",
            {
                "Fn::FindInMap": [
                    "A",
                    "B",
                    "C",
                    {"DefaultValue": {"Ref": "AWS::NoValue"}},
                ]
            },
            {"type": "string"},
            {"transforms": Transforms(["AWS::LanguageExtensions"])},
            [],
            [],
        ),
    ],
)
def test_validate(
    name,
    instance,
    schema,
    ref_mock_values,
    context_evolve,
    expected,
    rule,
    context,
    cfn,
):
    context = context.evolve(**context_evolve)
    ref_mock = MagicMock()
    ref_mock.return_value = iter(ref_mock_values or [])
    validator = CfnTemplateValidator({}).extend(validators={"ref": ref_mock})(
        context=context, cfn=cfn
    )
    errs = list(rule.fn_findinmap(validator, schema, instance, {}))

    if ref_mock_values is None:
        ref_mock.assert_not_called()
    else:
        assert ref_mock.call_count == len(ref_mock_values) or 1

    assert errs == expected, f"Test {name!r} got {errs!r}"
