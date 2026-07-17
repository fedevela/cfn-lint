"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from collections import deque

from cfnlint.context import Path, create_context_for_template
from cfnlint.jsonschema import CfnTemplateValidator
from cfnlint.rules.resources.stepfunctions.StateMachineDefinition import (
    StateMachineDefinition,
)
from cfnlint.template import Template


def _state_machine(placeholder, substitutions=None):
    properties = {
        "Definition": {
            "StartAt": "Invoke",
            "States": {
                "Invoke": {
                    "Type": "Task",
                    "Resource": placeholder,
                    "End": True,
                }
            },
        }
    }
    if substitutions is not None:
        properties["DefinitionSubstitutions"] = substitutions
    return {"Type": "AWS::StepFunctions::StateMachine", "Properties": properties}


def _errors(template, logical_id="StateMachine"):
    cfn = Template("", template, ["us-east-1"])
    path = Path(
        path=deque(["Resources", logical_id, "Properties", "Definition"]),
        cfn_path=deque(
            [
                "Resources",
                "AWS::StepFunctions::StateMachine",
                "Properties",
                "Definition",
            ]
        ),
    )
    context = create_context_for_template(cfn).evolve(path=path)
    validator = CfnTemplateValidator(context=context, cfn=cfn, schema={})
    definition = template["Resources"][logical_id]["Properties"]["Definition"]
    return list(StateMachineDefinition().validate(validator, {}, definition, {}))


def _error_signatures(template, logical_id="StateMachine"):
    return [(error.rule.id, error.validator) for error in _errors(template, logical_id)]


def test_gev_001_declared_inline_task_resource_placeholder_does_not_produce_e3601():
    """Contract: GEV-001."""
    template = {
        "Resources": {
            "StateMachine": _state_machine(
                "${UploadUsageActivityArn}",
                {"UploadUsageActivityArn": "arn:aws:lambda:us-east-1:123:function:x"},
            )
        }
    }

    assert _errors(template) == []


def test_gev_002_exact_local_placeholder_match_is_exempt_before_arn_pattern():
    """Contract: GEV-002."""
    template = {
        "Resources": {
            "StateMachine": _state_machine(
                "${UploadUsageActivityArn}",
                {"UploadUsageActivityArn": "not-an-arn"},
            )
        }
    }

    assert _errors(template) == []


def test_gev_003_declared_ref_placeholder_is_accepted_without_resolution():
    """Contract: GEV-003."""
    template = {
        "Resources": {
            "StateMachine": _state_machine(
                "${UploadUsageActivityArn}",
                {"UploadUsageActivityArn": {"Ref": "UploadUsageActivity"}},
            )
        }
    }

    assert _errors(template) == []


def test_gev_004_different_local_placeholder_name_is_not_exempt():
    """Contract: GEV-004, non-exact local declaration case."""
    template = {
        "Resources": {
            "StateMachine": _state_machine(
                "${UploadUsageActivityArn}",
                {"UploadUsageActivity": "value"},
            )
        }
    }

    assert _error_signatures(template) == [("E3601", "pattern")]


def test_gev_004_placeholder_declared_only_in_other_state_machine_is_not_exempt():
    """Contract: GEV-004, declaration on another state machine case."""
    template = {
        "Resources": {
            "FirstStateMachine": _state_machine("${UploadUsageActivityArn}"),
            "SecondStateMachine": _state_machine(
                "arn:aws:lambda:us-east-1:123456789012:function:second",
                {"UploadUsageActivityArn": {"Ref": "UploadUsageActivity"}},
            ),
        }
    }

    assert _error_signatures(template, "FirstStateMachine") == [("E3601", "pattern")]


def test_gev_004_placeholder_without_exact_local_declaration_is_not_exempt():
    """Contract: GEV-004, absent exact local declaration case."""
    template = {
        "Resources": {
            "StateMachine": _state_machine("${UploadUsageActivityArn}"),
        }
    }

    assert _error_signatures(template) == [("E3601", "pattern")]


def test_gev_005_concrete_malformed_task_resource_produces_arn_validation_error():
    """Contract: GEV-005, malformed concrete Task Resource case."""
    template = {
        "Resources": {
            "StateMachine": _state_machine("not-an-arn"),
        }
    }

    assert _error_signatures(template) == [("E3601", "pattern")]


def test_gev_005_unrelated_substitutions_do_not_exempt_malformed_concrete_resource():
    """Contract: GEV-005, unrelated DefinitionSubstitutions case."""
    template = {
        "Resources": {
            "StateMachine": _state_machine(
                "not-an-arn",
                {"UnrelatedArn": "arn:aws:lambda:us-east-1:123:function:x"},
            ),
        }
    }

    assert _error_signatures(template) == [("E3601", "pattern")]
