"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0

Issue #129 verification coverage for CFNSFN-010 and CFNSFN-013.
"""

import json

import pytest

from cfnlint import lint
from cfnlint.config import ManualArgs
from cfnlint.rules.resources.stepfunctions.StateMachineDefinition import (
    StateMachineDefinition,
)
from cfnlint.schema import PROVIDER_SCHEMA_MANAGER


_DEFINITION_KEYWORD = (
    "Resources/AWS::StepFunctions::StateMachine/Properties/Definition"
)
_DEFINITION_STRING_KEYWORD = (
    "Resources/AWS::StepFunctions::StateMachine/Properties/DefinitionString"
)
_SUBSTITUTIONS_PATH = [
    "Resources",
    "StateMachine",
    "Properties",
    "DefinitionSubstitutions",
]


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


def _state_machine_template(
    *, definition=None, definition_string=None, substitutions=None
):
    properties = {
        "RoleArn": "arn:aws:iam::123456789012:role/step-functions-test-role"
    }
    if definition is not None:
        properties["Definition"] = definition
    if definition_string is not None:
        properties["DefinitionString"] = definition_string
    if substitutions is not None:
        properties["DefinitionSubstitutions"] = substitutions

    return {
        "Resources": {
            "ReferencedActivity": {
                "Type": "AWS::StepFunctions::Activity",
            },
            "StateMachine": {
                "Type": "AWS::StepFunctions::StateMachine",
                "Properties": properties,
            },
        }
    }


def _lint_template(template):
    return lint(
        json.dumps(template),
        config=ManualArgs(regions=["us-east-1"]),
    )


def _matches_at(matches, path):
    return [match for match in matches if list(match.path)[: len(path)] == path]


def test_cfnsfn_010_when_definition_substitutions_map_has_invalid_shape_property_schema_finding_remains_observable():
    """A malformed declaration container remains owned by provider validation."""
    template = _state_machine_template(
        definition=_task_definition("arn:aws:states:::lambda:invoke"),
        substitutions=["not", "a", "map"],
    )

    matches = _lint_template(template)
    substitution_matches = _matches_at(matches, _SUBSTITUTIONS_PATH)

    assert substitution_matches
    assert any(match.rule.id == "E3012" for match in substitution_matches)
    assert all(match.rule.id != "E3601" for match in substitution_matches)


def test_cfnsfn_010_when_corresponding_placeholder_has_invalid_substitution_value_property_schema_finding_remains_observable():
    """E3601 deferral does not consume an invalid declaration-value finding."""
    template = _state_machine_template(
        definition=_task_definition("${DeferredResource}"),
        substitutions={"DeferredResource": ["not-a-schema-valid-value"]},
    )

    matches = _lint_template(template)
    substitution_matches = _matches_at(matches, _SUBSTITUTIONS_PATH)

    assert substitution_matches
    assert any(match.rule.id in {"E3012", "E3017"} for match in substitution_matches)
    assert all(match.rule.id != "E3601" for match in substitution_matches)
    assert all(match.rule.id != "E3601" for match in matches)


@pytest.mark.parametrize(
    "substitution_value",
    [
        pytest.param("activity-arn", id="schema_valid_string"),
        pytest.param(1, id="schema_valid_integer"),
        pytest.param(True, id="schema_valid_boolean_true"),
        pytest.param(0, id="schema_valid_falsy_zero"),
        pytest.param(False, id="schema_valid_falsy_boolean_false"),
        pytest.param(
            {"Ref": "ReferencedActivity"},
            id="schema_valid_cloudformation_intrinsic",
        ),
    ],
)
def test_cfnsfn_010_when_substitution_value_is_schema_valid_property_schema_accepts_while_e3601_defers_placeholder(
    substitution_value,
):
    """Every existing valid value form remains accepted across both owners."""
    template = _state_machine_template(
        definition=_task_definition("${DeferredResource}"),
        substitutions={"DeferredResource": substitution_value},
    )

    matches = _lint_template(template)

    assert _matches_at(matches, _SUBSTITUTIONS_PATH) == []
    assert all(match.rule.id != "E3601" for match in matches)


def test_cfnsfn_013_when_definition_string_contains_invalid_asl_lint_introduces_no_e3601_finding():
    """The intentionally disabled string interface does not invoke E3601."""
    template = _state_machine_template(definition_string="not-valid-ASL-json")

    matches = _lint_template(template)

    assert all(match.rule.id != "E3601" for match in matches)


def test_cfnsfn_013_when_provider_schema_has_both_definition_interfaces_e3601_registers_only_object_definition():
    """Schema availability does not broaden E3601's active keyword surface."""
    provider_schema = PROVIDER_SCHEMA_MANAGER.get_resource_schema(
        "us-east-1", "AWS::StepFunctions::StateMachine"
    ).schema
    rule = StateMachineDefinition()

    assert {"Definition", "DefinitionString"}.issubset(
        provider_schema["properties"]
    )
    assert list(rule.keywords) == [_DEFINITION_KEYWORD]
    assert _DEFINITION_STRING_KEYWORD not in rule.keywords
