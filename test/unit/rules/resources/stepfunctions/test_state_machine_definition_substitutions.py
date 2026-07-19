"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0

Issue #126 verification placeholders for CFNSFN-001, CFNSFN-002,
CFNSFN-003, and CFNSFN-009.
"""

from collections import deque

import pytest

from cfnlint.context import Path, create_context_for_template
from cfnlint.jsonschema import CfnTemplateValidator
from cfnlint.rules.resources.stepfunctions.StateMachineDefinition import (
    StateMachineDefinition,
)
from cfnlint.template import Template


pytestmark = pytest.mark.skip(
    reason="Phase 05 inert placeholders: enable during Malkhut implementation validation"
)


def _state_machine_template(definition, substitutions):
    return {
        "Resources": {
            "UploadUsageActivity": {
                "Type": "AWS::StepFunctions::Activity",
                "Properties": {"Name": "upload-usage"},
            },
            "ReportedStateMachine": {
                "Type": "AWS::StepFunctions::StateMachine",
                "Properties": {
                    "Definition": definition,
                    "DefinitionSubstitutions": substitutions,
                    "RoleArn": (
                        "arn:aws:iam::123456789012:role/step-functions-test-role"
                    ),
                },
            },
        }
    }


def _task_definition(resource="${UploadUsageActivityArn}"):
    return {
        "StartAt": "Upload usage",
        "States": {
            "Upload usage": {
                "Type": "Task",
                "Resource": resource,
                "End": True,
            }
        },
    }


def _e3601_errors(definition, substitutions):
    template = Template(
        "issue-126.yaml",
        _state_machine_template(definition, substitutions),
        ["us-east-1"],
    )
    context = create_context_for_template(template).evolve(
        path=Path(
            path=deque(
                [
                    "Resources",
                    "ReportedStateMachine",
                    "Properties",
                    "Definition",
                ]
            ),
            cfn_path=deque(
                [
                    "Resources",
                    "AWS::StepFunctions::StateMachine",
                    "Properties",
                    "Definition",
                ]
            ),
        )
    )
    validator = CfnTemplateValidator(schema={}, context=context, cfn=template)

    return list(StateMachineDefinition().validate(validator, {}, definition, {}))


def test_cfnsfn_001_cfnsfn_003_declared_activity_ref_task_resource_is_accepted():
    """A declared Activity Ref defers Task Resource ARN validation."""
    definition = _task_definition()
    substitutions = {"UploadUsageActivityArn": {"Ref": "UploadUsageActivity"}}

    assert _e3601_errors(definition, substitutions) == []


@pytest.mark.parametrize(
    "constraint,definition,substitutions",
    [
        pytest.param(
            "pattern",
            _task_definition("${DeferredResource}"),
            {"DeferredResource": "resolved-after-ASL-validation"},
            id="pattern_task_resource",
        ),
        pytest.param(
            "enum",
            {
                "StartAt": "Deferred state type",
                "States": {
                    "Deferred state type": {
                        "Type": "${DeferredStateType}",
                        "Resource": "arn:aws:states:::lambda:invoke",
                        "End": True,
                    }
                },
            },
            {"DeferredStateType": "Task"},
            id="enum_nested_state_type",
        ),
        pytest.param(
            "format-or-equivalent",
            {
                "StartAt": "Choose by timestamp",
                "States": {
                    "Choose by timestamp": {
                        "Type": "Choice",
                        "Choices": [
                            {
                                "Variable": "$.createdAt",
                                "TimestampEquals": "${DeferredTimestamp}",
                                "Next": "Done",
                            }
                        ],
                        "Default": "Done",
                    },
                    "Done": {"Type": "Succeed"},
                },
            },
            {"DeferredTimestamp": "2025-01-01T00:00:00Z"},
            id="format_or_equivalent_nested_choice_string",
        ),
    ],
)
def test_cfnsfn_002_declared_placeholder_in_any_definition_string_bypasses_constraint(
    constraint, definition, substitutions
):
    """Declared placeholders remain deferred at every nested string locus."""
    assert constraint in {"pattern", "enum", "format-or-equivalent"}
    assert _e3601_errors(definition, substitutions) == []


@pytest.mark.parametrize(
    "declaration_value",
    [
        pytest.param("activity-arn", id="schema_valid_string"),
        pytest.param(1, id="schema_valid_integer"),
        pytest.param(True, id="schema_valid_boolean_true"),
        pytest.param(0, id="schema_valid_falsy_zero"),
        pytest.param(False, id="schema_valid_falsy_boolean_false"),
        pytest.param(
            {"Ref": "UploadUsageActivity"},
            id="schema_valid_cloudformation_intrinsic",
        ),
    ],
)
def test_cfnsfn_009_substitution_key_presence_defers_regardless_of_value(
    declaration_value,
):
    """Presence, not declaration type, resolution, truthiness, controls deferral."""
    definition = _task_definition("${DeclaredByPresence}")
    substitutions = {"DeclaredByPresence": declaration_value}

    assert _e3601_errors(definition, substitutions) == []


def test_cfnsfn_009_all_schema_valid_declaration_forms_are_recognized_together():
    """Separate keys of every valid value form defer their own placeholders."""
    declarations = {
        "StringValue": "activity-arn",
        "IntegerValue": 1,
        "BooleanValue": True,
        "ZeroValue": 0,
        "FalseValue": False,
        "IntrinsicValue": {"Ref": "UploadUsageActivity"},
    }
    keys = list(declarations)
    states = {}
    for index, key in enumerate(keys):
        state = {
            "Type": "Task",
            "Resource": f"${{{key}}}",
        }
        if index == len(keys) - 1:
            state["End"] = True
        else:
            state["Next"] = keys[index + 1]
        states[key] = state
    definition = {"StartAt": keys[0], "States": states}

    assert _e3601_errors(definition, declarations) == []


def test_cfnsfn_001_cfnsfn_009_complete_valid_definition_with_deferred_resource_passes():
    """E3601 accepts the complete valid ASL object containing a declared Resource."""
    definition = _task_definition()
    substitutions = {"UploadUsageActivityArn": {"Ref": "UploadUsageActivity"}}

    assert _e3601_errors(definition, substitutions) == []
