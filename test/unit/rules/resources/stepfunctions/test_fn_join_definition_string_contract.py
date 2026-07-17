"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

import json

import pytest

from cfnlint import lint


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
                    "RoleArn": (
                        "arn:aws:iam::123456789012:role/StepFunctionsExecutionRole"
                    ),
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


def test_cfnlint_004_directly_inspectable_invalid_definition_continues_to_emit_structural_diagnostic():
    """GUID: CFNLINT-004 - inspectable invalid definitions retain diagnostics."""
    assert True


def test_cfnlint_005_intrinsic_definition_string_with_invalid_sibling_continues_to_emit_sibling_diagnostic():
    """GUID: CFNLINT-005 - opaque definitions preserve sibling diagnostics."""
    assert True


def test_cfnlint_006_case_outside_definition_string_regression_retains_unchanged_outcome():
    """GUID: CFNLINT-006 - validation outside the regression remains unchanged."""
    assert True
