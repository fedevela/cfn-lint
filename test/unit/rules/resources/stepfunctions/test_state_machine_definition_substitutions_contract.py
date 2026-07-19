"""Durable verification obligations for substitution-aware Definition validation."""

from __future__ import annotations

import json

import pytest

from cfnlint.rules.resources.stepfunctions.StateMachineDefinition import (
    StateMachineDefinition,
)

# Requirement-bearing test names intentionally retain their complete contracts.
# ruff: noqa: E501


pytestmark = pytest.mark.skip(
    reason="Phase 05 placeholder: activate during Malkhut executable validation"
)


RESOURCE_PATTERN = "pattern"
RESOURCE_TYPE = "type"


@pytest.fixture
def rule():
    return StateMachineDefinition()


def _valid_definition(resource="arn:aws:states:::lambda:invoke"):
    return {
        "StartAt": "Task",
        "States": {
            "Task": {
                "Type": "Task",
                "Resource": resource,
                "End": True,
            }
        },
    }


def _findings(rule, validator, properties):
    return list(rule.validate(validator, {}, properties, {}))


def _signatures(findings):
    return [(finding.validator, list(finding.path)) for finding in findings]


def test_smdef_005_valid_directly_inspectable_definition_object_has_no_structural_findings(
    rule, validator
):
    properties = {"Definition": _valid_definition()}

    assert _findings(rule, validator, properties) == []


def test_smdef_005_concrete_definition_json_string_decoding_to_valid_asl_has_no_structural_findings(
    rule, validator
):
    properties = {"Definition": json.dumps(_valid_definition())}

    assert _findings(rule, validator, properties) == []


def test_smdef_006_invalid_directly_inspectable_definition_object_reports_every_established_definition_relative_path(
    rule, validator
):
    properties = {"Definition": {"States": {"NoType": {}}}}

    assert _signatures(_findings(rule, validator, properties)) == [
        ("required", ["Definition", "States", "NoType"]),
        ("required", ["Definition"]),
    ]


def test_smdef_006_invalid_concrete_definition_json_string_preserves_definition_relative_and_decoded_child_paths(
    rule, validator
):
    properties = {"Definition": json.dumps({"States": {"NoType": {}}})}

    findings = _findings(rule, validator, properties)

    assert _signatures(findings) == [
        ("required", ["Definition", "States", "NoType"]),
        ("required", ["Definition"]),
    ]
    assert "at 'States/NoType'" in findings[0].message


def test_smdef_007_object_valued_sibling_substitutions_authorize_an_exact_declared_placeholder_in_definition(
    rule, validator
):
    properties = {
        "DefinitionSubstitutions": {"function_arn": {"Ref": "FunctionArn"}},
        "Definition": _valid_definition("${function_arn}"),
    }

    assert _findings(rule, validator, properties) == []


def test_smdef_008_substitutions_preserve_undeclared_placeholder_and_unrelated_invalid_value_findings(
    rule, validator
):
    properties = {
        "DefinitionSubstitutions": {"declared": "value"},
        "Definition": {
            "StartAt": "UndeclaredPlaceholder",
            "States": {
                "UndeclaredPlaceholder": {
                    "Type": "Task",
                    "Resource": "${undeclared}",
                    "Next": "InvalidValue",
                },
                "InvalidValue": {
                    "Type": "Task",
                    "Resource": [],
                    "End": True,
                },
            },
        },
    }

    assert _signatures(_findings(rule, validator, properties)) == [
        (
            RESOURCE_PATTERN,
            ["Definition", "States", "UndeclaredPlaceholder", "Resource"],
        ),
        (RESOURCE_TYPE, ["Definition", "States", "InvalidValue", "Resource"]),
    ]


def test_smdef_009_absent_definition_substitutions_does_not_authorize_a_placeholder(
    rule, validator
):
    properties = {"Definition": _valid_definition("${undeclared}")}

    assert _signatures(_findings(rule, validator, properties)) == [
        (RESOURCE_PATTERN, ["Definition", "States", "Task", "Resource"]),
    ]


def test_smdef_009_non_object_definition_substitutions_does_not_infer_or_authorize_keys(
    rule, validator
):
    properties = {
        "DefinitionSubstitutions": "function_arn",
        "Definition": _valid_definition("${function_arn}"),
    }

    assert _signatures(_findings(rule, validator, properties)) == [
        (RESOURCE_PATTERN, ["Definition", "States", "Task", "Resource"]),
    ]


@pytest.mark.parametrize(
    ("definition", "expected"),
    [
        (_valid_definition(), []),
        (
            {"States": {"NoType": {}}},
            [
                ("required", ["Definition", "States", "NoType"]),
                ("required", ["Definition"]),
            ],
        ),
    ],
    ids=["established-valid-definition", "established-invalid-definition"],
)
def test_smdef_005_smdef_006_ordinary_e3601_definition_cases_retain_established_outcomes_and_paths(
    definition, expected, rule, validator
):
    properties = {"Definition": definition}

    assert _signatures(_findings(rule, validator, properties)) == expected
