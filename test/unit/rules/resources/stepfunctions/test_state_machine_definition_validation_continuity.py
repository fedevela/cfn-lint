"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0

Issue #128 verification coverage for CFNSFN-006, CFNSFN-007,
CFNSFN-008, and CFNSFN-012.
"""

from collections import deque

from cfnlint.context import Path, create_context_for_template
from cfnlint.jsonschema import CfnTemplateValidator
from cfnlint.rules.resources.stepfunctions.StateMachineDefinition import (
    StateMachineDefinition,
)
from cfnlint.template import Template


def _task_state(**overrides):
    state = {
        "Type": "Task",
        "Resource": "arn:aws:states:::lambda:invoke",
        "End": True,
    }
    state.update(overrides)
    return state


def _definition(state, *, include_declared_substitution=True):
    states = {"State under test": state}
    substitutions = None
    if include_declared_substitution:
        states["Deferred task"] = _task_state(Resource="${DeferredResource}")
        substitutions = {"DeferredResource": "resolved-after-ASL-validation"}

    return {"StartAt": "State under test", "States": states}, substitutions


def _e3601_errors(definition, substitutions=None):
    properties = {
        "Definition": definition,
        "RoleArn": "arn:aws:iam::123456789012:role/step-functions-test-role",
    }
    if substitutions is not None:
        properties["DefinitionSubstitutions"] = substitutions

    template = Template(
        "issue-128.yaml",
        {
            "Resources": {
                "StateMachine": {
                    "Type": "AWS::StepFunctions::StateMachine",
                    "Properties": properties,
                }
            }
        },
        ["us-east-1"],
    )
    context = create_context_for_template(template).evolve(
        path=Path(
            path=deque(
                ["Resources", "StateMachine", "Properties", "Definition"]
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


def _has_finding(errors, validator, path):
    return any(
        error.validator == validator and list(error.path) == path for error in errors
    )


def test_cfnsfn_006_when_task_resource_is_concrete_and_invalid_e3601_reports_pattern_at_resource(
):
    """A concrete invalid Task Resource retains its format finding and path."""
    definition, substitutions = _definition(
        _task_state(Resource="not-an-asl-resource")
    )

    errors = _e3601_errors(definition, substitutions)

    assert _has_finding(
        errors, "pattern", ["States", "State under test", "Resource"]
    )


def test_cfnsfn_007_when_substitution_exists_and_task_resource_is_missing_e3601_reports_required_at_state(
):
    """A declared substitution elsewhere does not hide a required field."""
    state = _task_state()
    del state["Resource"]
    definition, substitutions = _definition(state)

    errors = _e3601_errors(definition, substitutions)

    assert _has_finding(errors, "required", ["States", "State under test"])


def test_cfnsfn_007_when_substitution_exists_and_state_has_unsupported_field_e3601_reports_additional_properties_at_state(
):
    """A declared substitution elsewhere does not hide an unsupported field."""
    definition, substitutions = _definition(_task_state(Unsupported=True))

    errors = _e3601_errors(definition, substitutions)

    assert _has_finding(
        errors,
        "additionalProperties",
        ["States", "State under test", "Unsupported"],
    )


def test_cfnsfn_007_when_substitution_exists_and_state_type_is_invalid_e3601_reports_enum_at_type(
):
    """A declared substitution elsewhere does not hide an invalid state type."""
    definition, substitutions = _definition(_task_state(Type="Unsupported"))

    errors = _e3601_errors(definition, substitutions)

    assert _has_finding(errors, "enum", ["States", "State under test", "Type"])


def test_cfnsfn_008_when_substitution_exists_and_task_has_neither_next_nor_end_e3601_reports_required_xor_at_state(
):
    """A deferred value elsewhere does not hide a missing termination choice."""
    state = _task_state()
    del state["End"]
    definition, substitutions = _definition(state)

    errors = _e3601_errors(definition, substitutions)

    assert _has_finding(errors, "requiredXor", ["States", "State under test"])


def test_cfnsfn_008_when_substitution_exists_and_task_has_both_next_and_end_e3601_reports_required_xor_at_each_property(
):
    """A deferred value elsewhere does not hide mutually exclusive outcomes."""
    definition, substitutions = _definition(_task_state(Next="Deferred task"))

    errors = _e3601_errors(definition, substitutions)

    assert _has_finding(
        errors, "requiredXor", ["States", "State under test", "Next"]
    )
    assert _has_finding(
        errors, "requiredXor", ["States", "State under test", "End"]
    )


def test_cfnsfn_008_when_substitution_exists_and_task_next_is_empty_e3601_reports_pattern_at_next(
):
    """A deferred value elsewhere does not hide an invalid Next value."""
    state = _task_state(Next="")
    del state["End"]
    definition, substitutions = _definition(state)

    errors = _e3601_errors(definition, substitutions)

    assert _has_finding(errors, "pattern", ["States", "State under test", "Next"])


def test_cfnsfn_012_when_object_definition_has_no_placeholders_and_is_valid_e3601_acceptance_is_unchanged(
):
    """A valid ordinary object Definition retains zero E3601 findings."""
    definition, _ = _definition(
        _task_state(), include_declared_substitution=False
    )

    assert _e3601_errors(definition) == []


def test_cfnsfn_012_when_object_definition_has_no_placeholders_and_resource_is_invalid_e3601_pattern_and_path_are_unchanged(
):
    """An invalid ordinary object Definition retains its finding and path."""
    definition, _ = _definition(
        _task_state(Resource="not-an-asl-resource"),
        include_declared_substitution=False,
    )

    errors = _e3601_errors(definition)

    assert _has_finding(
        errors, "pattern", ["States", "State under test", "Resource"]
    )
