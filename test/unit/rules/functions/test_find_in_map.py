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
from cfnlint.rules.functions._BaseFn import BaseFn
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
    """Verification contracts for GUID: E1011-003."""

    def test_excessive_depth_after_message_enhancement_remains_invalid_with_e1011(
        self,
        rule,
        context,
        cfn,
    ):
        """An excessive-depth lookup remains invalid and detectable as E1011."""
        validator = CfnTemplateValidator({})(context=context, cfn=cfn)

        errors = list(
            rule.fn_findinmap(
                validator,
                {"type": "string"},
                {"Fn::FindInMap": ["A", "B", "C", "D"]},
                {},
            )
        )

        assert rule.id == "E1011"
        assert errors == [
            ValidationError(
                "FindInMap supports no more than two lookup levels",
                path=deque(["Fn::FindInMap"]),
                schema_path=deque(["maxItems"]),
                validator="fn_findinmap",
            )
        ]


class TestE1011004FindInMapSupportedDepthPreservation:
    """Verification contracts for GUID: E1011-004."""

    def test_supported_depth_after_message_enhancement_remains_valid_without_e1011(
        self,
        rule,
        context,
        cfn,
    ):
        """A supported-depth lookup remains accepted without a new E1011 finding."""
        validator = CfnTemplateValidator({})(context=context, cfn=cfn)

        errors = list(
            rule.fn_findinmap(
                validator,
                {"type": "string"},
                {"Fn::FindInMap": ["A", "B", "C"]},
                {},
            )
        )

        assert errors == []


class TestE1011003E1011004FindInMapBoundaryClassificationPreservation:
    """Verification contract for GUIDs: E1011-003, E1011-004."""

    def test_boundary_fixtures_before_and_after_enhancement_only_change_e1011_text(
        self,
        rule,
        context,
        cfn,
    ):
        """Boundary classifications remain unchanged when E1011 text changes."""
        validator = CfnTemplateValidator({})(context=context, cfn=cfn)
        schema = {"type": "string"}
        excessive = {"Fn::FindInMap": ["A", "B", "C", "D"]}
        supported = {"Fn::FindInMap": ["A", "B", "C"]}

        before_validator = validator.evolve(
            context=validator.context.evolve(resources={})
        )
        before_excessive = list(
            BaseFn.validate(rule, before_validator, schema, excessive, {})
        )
        after_excessive = list(
            rule.fn_findinmap(validator, schema, excessive, {})
        )
        before_supported = list(
            BaseFn.validate(rule, before_validator, schema, supported, {})
        )
        after_supported = list(rule.fn_findinmap(validator, schema, supported, {}))

        assert len(before_excessive) == len(after_excessive) == 1
        assert before_supported == after_supported == []
        assert before_excessive[0].message == (
            "['A', 'B', 'C', 'D'] is too long (3)"
        )
        assert after_excessive[0].message == (
            "FindInMap supports no more than two lookup levels"
        )
        assert before_excessive[0].path == after_excessive[0].path
        assert before_excessive[0].schema_path == after_excessive[0].schema_path
        assert before_excessive[0].validator == after_excessive[0].validator
        assert before_excessive[0].context == after_excessive[0].context
        assert before_excessive[0].cause == after_excessive[0].cause
        assert before_excessive[0].path_override == after_excessive[0].path_override


class TestE1011005ExcessiveFindInMapDiagnosticEnvelopePreservation:
    """Verification contracts for GUID: E1011-005."""

    @staticmethod
    def _before_and_after(rule, context, cfn):
        validator = CfnTemplateValidator({})(context=context, cfn=cfn)
        schema = {"type": "string"}
        instance = {"Fn::FindInMap": ["A", "B", "C", "D"]}
        before_validator = validator.evolve(
            context=validator.context.evolve(resources={})
        )

        before = list(BaseFn.validate(rule, before_validator, schema, instance, {}))
        after = list(rule.fn_findinmap(validator, schema, instance, {}))

        assert len(before) == len(after) == 1
        return before[0], after[0]

    def test_e1011_005_excessive_lookup_after_enhancement_retains_e1011_identifier(
        self, rule, context, cfn
    ):
        """The enhanced excessive-lookup finding remains identified as E1011."""
        _, after = self._before_and_after(rule, context, cfn)

        assert rule.id == "E1011"
        assert after.validator == "fn_findinmap"

    def test_e1011_005_excessive_lookup_after_enhancement_retains_location_and_path(
        self, rule, context, cfn
    ):
        """The enhanced finding retains its diagnostic location and path."""
        before, after = self._before_and_after(rule, context, cfn)

        assert after.path == before.path == deque(["Fn::FindInMap"])
        assert after.relative_path == before.relative_path
        assert after.absolute_path == before.absolute_path
        assert after.path_override == before.path_override

    def test_e1011_005_excessive_lookup_after_enhancement_retains_metadata(
        self, rule, context, cfn
    ):
        """The enhanced finding retains all diagnostic metadata."""
        before, after = self._before_and_after(rule, context, cfn)
        location_fields = {"path", "relative_path", "path_override"}
        before_metadata = {
            key: value
            for key, value in vars(before).items()
            if key not in {"message", *location_fields}
        }
        after_metadata = {
            key: value
            for key, value in vars(after).items()
            if key not in {"message", *location_fields}
        }

        assert after_metadata == before_metadata

    def test_e1011_005_excessive_lookup_after_enhancement_changes_only_message_text(
        self, rule, context, cfn
    ):
        """Only the targeted excessive-lookup message text changes."""
        before, after = self._before_and_after(rule, context, cfn)

        assert before.message == "['A', 'B', 'C', 'D'] is too long (3)"
        assert after.message == "FindInMap supports no more than two lookup levels"
        assert {
            key: value for key, value in vars(after).items() if key != "message"
        } == {
            key: value for key, value in vars(before).items() if key != "message"
        }


class TestE1011006UnrelatedValidationAndWordingPreservation:
    """Verification contracts for GUID: E1011-006."""

    def test_e1011_006_after_enhancement_unrelated_condition_keeps_behavior_and_wording(
        self, rule, context, cfn
    ):
        """An unrelated validation condition retains behavior and wording."""
        validator = CfnTemplateValidator({})(context=context, cfn=cfn)
        schema = {"type": "string"}
        instance = {"Fn::FindInMap": {"foo": "bar"}}
        before_validator = validator.evolve(
            context=validator.context.evolve(resources={})
        )

        before = list(BaseFn.validate(rule, before_validator, schema, instance, {}))
        after = list(rule.fn_findinmap(validator, schema, instance, {}))

        assert after == before
        assert after[0].message == "{'foo': 'bar'} is not of type 'array'"

    def test_e1011_006_unrelated_suite_after_enhancement_retains_findings_and_wording(
        self, rule, context, cfn
    ):
        """The unrelated suite retains its findings and diagnostic wording."""
        validator = CfnTemplateValidator({})(context=context, cfn=cfn)
        schema = {"type": "string"}
        cases = [
            (
                {"Fn::FindInMap": [{"Fn::GetAtt": "MyResource.Arn"}, "foo", "bar"]},
                "{'Fn::GetAtt': 'MyResource.Arn'} is not of type 'string'",
            ),
            ({"Fn::FindInMap": ["A", "B"]}, "['A', 'B'] is too short (3)"),
        ]

        findings = [
            list(rule.fn_findinmap(validator, schema, instance, {}))
            for instance, _ in cases
        ]

        assert [len(errors) for errors in findings] == [1, 1]
        assert [errors[0].message for errors in findings] == [
            message for _, message in cases
        ]
        assert all(errors[0].validator == "fn_findinmap" for errors in findings)


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
