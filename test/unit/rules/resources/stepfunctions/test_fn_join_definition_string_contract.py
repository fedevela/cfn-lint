"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

import json

import pytest

from cfnlint import lint


ROLE_ARN = "arn:aws:iam::123456789012:role/StepFunctionsExecutionRole"


def _lint_state_machine(properties):
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "StateMachine": {
                "Type": "AWS::StepFunctions::StateMachine",
                "Properties": {"RoleArn": ROLE_ARN, **properties},
            }
        },
    }

    return lint(json.dumps(template))


@pytest.fixture(scope="module")
def reproduction_matches():
    """Validate the JSON reproduction once for all traced requirements."""
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "StateMachine": {
                "Type": "AWS::StepFunctions::StateMachine",
                "Properties": {
                    "DefinitionString": {
                        "Fn::Join": [
                            "\n",
                            [
                                "{",
                                '"StartAt": "Hello",',
                                '"States": {',
                                '"Hello": {"Type": "Pass", "End": true}',
                                "}",
                                "}",
                            ],
                        ]
                    },
                    "RoleArn": ROLE_ARN,
                },
            }
        },
    }

    return lint(json.dumps(template))


def test_cfnlint_001_fn_join_definition_string_does_not_emit_e1022(
    reproduction_matches,
):
    """GUID: CFNLINT-001 - Fn::Join DefinitionString transitions without E1022."""
    assert all(match.rule.id != "E1022" for match in reproduction_matches)


def test_cfnlint_002_uninspectable_definition_does_not_emit_e3601_missing_start_at(
    reproduction_matches,
):
    """GUID: CFNLINT-002 - opaque DefinitionString has no missing StartAt E3601."""
    assert not any(
        match.rule.id == "E3601" and "'StartAt' is a required property" in match.message
        for match in reproduction_matches
    )


def test_cfnlint_002_uninspectable_definition_does_not_emit_e3601_missing_states(
    reproduction_matches,
):
    """GUID: CFNLINT-002 - opaque DefinitionString has no missing States E3601."""
    assert not any(
        match.rule.id == "E3601" and "'States' is a required property" in match.message
        for match in reproduction_matches
    )


def test_cfnlint_003_fn_join_definition_string_reproduction_validation_succeeds(
    reproduction_matches,
):
    """GUID: CFNLINT-003 - supplied reproduction transitions to validation success."""
    assert reproduction_matches == []


def test_cfnlint_004_inspectable_invalid_definition_keeps_diagnostic():
    """GUID: CFNLINT-004 - inspectable invalid definitions retain diagnostics."""
    matches = _lint_state_machine(
        {
            "Definition": {
                "States": {"Hello": {"Type": "Pass", "End": True}},
            }
        }
    )

    assert any(
        match.rule.id == "E3601"
        and "'StartAt' is a required property" in match.message
        for match in matches
    )


def test_cfnlint_005_opaque_definition_keeps_sibling_diagnostic():
    """GUID: CFNLINT-005 - opaque definitions preserve sibling diagnostics."""
    matches = _lint_state_machine(
        {
            "DefinitionString": {"Fn::Join": ["", ["{}"]]},
            "StateMachineType": "INVALID",
        }
    )

    assert any(
        match.rule.id == "E3030"
        and "StateMachineType" in match.path
        and "INVALID" in match.message
        for match in matches
    )


def test_cfnlint_006_literal_definition_string_keeps_outcome():
    """GUID: CFNLINT-006 - validation outside the regression remains unchanged."""
    definition = {
        "StartAt": "Hello",
        "States": {"Hello": {"Type": "Pass", "End": True}},
    }

    matches = _lint_state_machine({"DefinitionString": json.dumps(definition)})

    assert matches == []
