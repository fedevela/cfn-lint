"""Durable verification obligations for the DefinitionString contract."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cfnlint import lint

# Requirement-bearing test names intentionally retain their complete contracts.
# ruff: noqa: E501


pytestmark = pytest.mark.skip(
    reason="SMDEF verification placeholders: activate during implementation"
)

REPRODUCTION = Path("test/fixtures/templates/issues/3769.json")
PROPERTY_PATH = [
    "Resources",
    "StateMachine",
    "Properties",
    "DefinitionString",
]


def _template(definition_string):
    return {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "StateMachine": {
                "Type": "AWS::StepFunctions::StateMachine",
                "Properties": {
                    "DefinitionString": definition_string,
                    "RoleArn": (
                        "arn:aws:iam::111122223333:role/StateMachineExecutionRole"
                    ),
                },
            }
        },
    }


def _relevant_matches(source):
    relevant_rule_ids = {"E1022", "E3012", "E3033", "E3601"}
    return [match for match in lint(source) if match.rule.id in relevant_rule_ids]


def test_smdef_001_smdef_003_reported_json_fn_join_lints_without_e1022_or_e3601():
    """SMDEF-001/SMDEF-003: lint the exact reported JSON reproduction cleanly."""
    matches = _relevant_matches(REPRODUCTION.read_text(encoding="utf-8"))

    assert [match for match in matches if match.rule.id in {"E1022", "E3601"}] == []


@pytest.mark.parametrize(
    ("source_format", "source"),
    [
        (
            "JSON",
            json.dumps(_template({"Fn::Sub": "${AWS::Partition}-definition"})),
        ),
        (
            "YAML",
            """\
AWSTemplateFormatVersion: 2010-09-09
Resources:
  StateMachine:
    Type: AWS::StepFunctions::StateMachine
    Properties:
      DefinitionString: !Sub "${AWS::Partition}-definition"
      RoleArn: arn:aws:iam::111122223333:role/StateMachineExecutionRole
""",
        ),
    ],
)
def test_smdef_001_smdef_002_json_and_yaml_valid_string_intrinsics_are_owned_by_function_rules(
    source_format, source
):
    """SMDEF-001/SMDEF-002: supported string intrinsics bypass E3601."""
    matches = _relevant_matches(source)

    assert [match for match in matches if match.rule.id == "E3601"] == [], source_format
    assert [match for match in matches if match.rule.id == "E3012"] == [], source_format


@pytest.mark.parametrize(
    ("source_format", "source"),
    [
        ("JSON", json.dumps(_template("not Amazon States Language"))),
        (
            "YAML",
            """\
AWSTemplateFormatVersion: 2010-09-09
Resources:
  StateMachine:
    Type: AWS::StepFunctions::StateMachine
    Properties:
      DefinitionString: "not Amazon States Language"
      RoleArn: arn:aws:iam::111122223333:role/StateMachineExecutionRole
""",
        ),
    ],
)
def test_smdef_002_json_and_yaml_concrete_definition_strings_are_not_parsed_by_e3601(
    source_format, source
):
    """SMDEF-002: concrete DefinitionString values are outside E3601."""
    matches = _relevant_matches(source)

    assert [match for match in matches if match.rule.id == "E3601"] == [], source_format


def test_smdef_004_malformed_fn_join_reports_e1022_at_definition_string_intrinsic_path_without_e3601():
    """SMDEF-004: malformed Join remains an E1022-owned intrinsic error."""
    source = json.dumps(_template({"Fn::Join": ["-", "not-an-array"]}))

    matches = _relevant_matches(source)
    e1022_matches = [match for match in matches if match.rule.id == "E1022"]

    assert e1022_matches
    assert all(match.path[:4] == PROPERTY_PATH for match in e1022_matches)
    assert all(match.path[4] == "Fn::Join" for match in e1022_matches)
    assert [match for match in matches if match.rule.id == "E3601"] == []


def test_smdef_010_non_string_concrete_definition_string_reports_resource_schema_type_only():
    """SMDEF-010: resource schema retains concrete string-type ownership."""
    matches = _relevant_matches(json.dumps(_template(["not", "a", "string"])))

    assert [match for match in matches if match.rule.id == "E3012"]
    assert [match for match in matches if match.rule.id == "E3601"] == []


@pytest.mark.parametrize(
    "value", ["", "x" * 1048577], ids=["below-minimum", "above-maximum"]
)
def test_smdef_010_out_of_bounds_concrete_definition_strings_report_resource_schema_length_only(
    value,
):
    """SMDEF-010: resource schema retains minimum/maximum length ownership."""
    matches = _relevant_matches(json.dumps(_template(value)))

    assert [match for match in matches if match.rule.id == "E3033"]
    assert [match for match in matches if match.rule.id == "E3601"] == []


@pytest.mark.parametrize("value", ["x", "x" * 1048576], ids=["minimum", "maximum"])
def test_smdef_010_inclusive_boundary_definition_strings_pass_resource_schema_without_e3601(
    value,
):
    """SMDEF-010: inclusive string bounds pass and E3601 remains absent."""
    matches = _relevant_matches(json.dumps(_template(value)))

    assert [
        match
        for match in matches
        if match.rule.id in {"E3012", "E3033", "E3601"}
    ] == []
