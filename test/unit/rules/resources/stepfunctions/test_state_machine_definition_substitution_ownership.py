"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0

Issue #127 verification obligations for CFNSFN-004, CFNSFN-005, and
CFNSFN-011.
"""

from collections import deque

from cfnlint.context import Path, create_context_for_template
from cfnlint.jsonschema import CfnTemplateValidator
from cfnlint.rules.resources.stepfunctions.StateMachineDefinition import (
    StateMachineDefinition,
)
from cfnlint.template import Template


def _task_definition(resource):
    return {
        "StartAt": "Invoke activity",
        "States": {
            "Invoke activity": {
                "Type": "Task",
                "Resource": resource,
                "End": True,
            }
        },
    }


def _state_machine_resource(resource, substitutions=None):
    properties = {
        "Definition": _task_definition(resource),
        "RoleArn": "arn:aws:iam::123456789012:role/step-functions-test-role",
    }
    if substitutions is not None:
        properties["DefinitionSubstitutions"] = substitutions

    return {
        "Type": "AWS::StepFunctions::StateMachine",
        "Properties": properties,
    }


def _e3601_errors(template_body, resource_name):
    definition = template_body["Resources"][resource_name]["Properties"]["Definition"]
    template = Template("issue-127.yaml", template_body, ["us-east-1"])
    context = create_context_for_template(template).evolve(
        path=Path(
            path=deque(["Resources", resource_name, "Properties", "Definition"]),
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


def _has_resource_pattern_finding(errors):
    return any(
        error.validator == "pattern" and list(error.path)[-1:] == ["Resource"]
        for error in errors
    )


def test_cfnsfn_004_when_task_resource_placeholder_is_undeclared_e3601_pattern_finding_remains():
    """An undeclared standalone Resource placeholder receives no exemption."""
    template = {
        "Resources": {
            "StateMachine": _state_machine_resource("${UploadUsageActivityArn}")
        }
    }

    errors = _e3601_errors(template, "StateMachine")

    assert _has_resource_pattern_finding(errors)


def test_cfnsfn_005_when_only_first_owner_declares_shared_placeholder_e3601_reports_second_only():
    """One state machine cannot authorize another state machine's placeholder."""
    template = {
        "Resources": {
            "DeclaringStateMachine": _state_machine_resource(
                "${SharedActivityArn}",
                {"SharedActivityArn": "activity-arn"},
            ),
            "UndeclaringStateMachine": _state_machine_resource(
                "${SharedActivityArn}"
            ),
        }
    }

    declaring_errors = _e3601_errors(template, "DeclaringStateMachine")
    undeclaring_errors = _e3601_errors(template, "UndeclaringStateMachine")

    assert not _has_resource_pattern_finding(declaring_errors)
    assert _has_resource_pattern_finding(undeclaring_errors)


def test_cfnsfn_011_when_embedded_placeholders_are_all_declared_e3601_defers_complete_string():
    """Literal text with multiple declared placeholders is wholly deferred."""
    template = {
        "Resources": {
            "StateMachine": _state_machine_resource(
                "not-an-arn-${ActivityPrefix}-${ActivityName}",
                {
                    "ActivityPrefix": "activity-prefix",
                    "ActivityName": "activity-name",
                },
            )
        }
    }

    errors = _e3601_errors(template, "StateMachine")

    assert not _has_resource_pattern_finding(errors)


def test_cfnsfn_011_when_comma_delimited_keys_are_all_declared_e3601_defers_complete_form():
    """A comma-delimited form is deferred when every key is declared."""
    template = {
        "Resources": {
            "StateMachine": _state_machine_resource(
                "${ActivityPrefix,ActivityName}",
                {
                    "ActivityPrefix": "activity-prefix",
                    "ActivityName": "activity-name",
                },
            )
        }
    }

    errors = _e3601_errors(template, "StateMachine")

    assert not _has_resource_pattern_finding(errors)


def test_cfnsfn_004_cfnsfn_011_when_embedded_placeholder_is_partially_declared_e3601_pattern_finding_remains():
    """An embedded string is not exempt when any referenced key is absent."""
    template = {
        "Resources": {
            "StateMachine": _state_machine_resource(
                "not-an-arn-${DeclaredPrefix}-${MissingName}",
                {"DeclaredPrefix": "activity-prefix"},
            )
        }
    }

    errors = _e3601_errors(template, "StateMachine")

    assert _has_resource_pattern_finding(errors)


def test_cfnsfn_004_cfnsfn_011_when_comma_delimited_keys_are_partially_declared_e3601_pattern_finding_remains():
    """A comma-delimited form is not exempt when any key is absent."""
    template = {
        "Resources": {
            "StateMachine": _state_machine_resource(
                "${DeclaredPrefix,MissingName}",
                {"DeclaredPrefix": "activity-prefix"},
            )
        }
    }

    errors = _e3601_errors(template, "StateMachine")

    assert _has_resource_pattern_finding(errors)
