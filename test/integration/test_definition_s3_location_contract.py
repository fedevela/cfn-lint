"""Durable verification obligations for the DefinitionS3Location contract."""

from __future__ import annotations

import json

from cfnlint import lint

# Requirement-bearing test names intentionally retain their complete contracts.
# ruff: noqa: E501


LOCATION_PATH = [
    "Resources",
    "StateMachine",
    "Properties",
    "DefinitionS3Location",
]


def _template(definition_s3_location):
    return {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "StateMachine": {
                "Type": "AWS::StepFunctions::StateMachine",
                "Properties": {
                    "DefinitionS3Location": definition_s3_location,
                    "RoleArn": (
                        "arn:aws:iam::111122223333:role/StateMachineExecutionRole"
                    ),
                },
            }
        },
    }


def _relevant_matches(definition_s3_location):
    relevant_rule_ids = {"E3002", "E3003", "E3012", "E3601"}
    source = json.dumps(_template(definition_s3_location))
    return [match for match in lint(source) if match.rule.id in relevant_rule_ids]


def test_smdef_011_valid_definition_s3_location_lints_without_inline_asl_findings():
    """SMDEF-011: a provider-valid external definition remains outside E3601."""
    matches = _relevant_matches(
        {"Bucket": "state-machine-definitions", "Key": "workflow.asl.json"}
    )

    assert matches == []


def test_smdef_011_invalid_definition_s3_location_reports_resource_schema_path_without_e3601():
    """SMDEF-011: the provider schema alone owns an invalid external location."""
    matches = _relevant_matches({"Bucket": "state-machine-definitions"})
    schema_matches = [match for match in matches if match.rule.id == "E3003"]

    assert schema_matches
    assert all(match.path == LOCATION_PATH for match in schema_matches)
    assert [match for match in matches if match.rule.id == "E3601"] == []


def test_smdef_011_definition_s3_location_without_inline_definition_does_not_require_start_at_or_states():
    """SMDEF-011: no inline Definition means no E3601 ASL-required findings."""
    matches = _relevant_matches(
        {"Bucket": "state-machine-definitions", "Key": "workflow.asl.json"}
    )
    e3601_matches = [match for match in matches if match.rule.id == "E3601"]

    assert e3601_matches == []
