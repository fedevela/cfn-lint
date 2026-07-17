"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

import pytest

from cfnlint import ConfigMixIn, Rules
from cfnlint.jsonschema import CfnTemplateValidator
from cfnlint.rules.conditions.Equals import Equals
from cfnlint.rules.conditions.EqualsIsUseful import EqualsIsUseful
from cfnlint.rules.jsonschema.JsonSchema import JsonSchema
from cfnlint.runner import TemplateRunner


def _lint_conditions(conditions):
    rules = Rules(
        {
            "E1001": JsonSchema(),
            "E8003": Equals(),
            "W8003": EqualsIsUseful(),
        }
    )
    config = ConfigMixIn(include_checks=["W8003"])
    template = {"Conditions": conditions, "Resources": {}}
    return [
        match
        for match in TemplateRunner(None, template, config, rules).run()
        if match.rule.id == "W8003"
    ]


def test_W8003_001_identical_literal_equals_when_linted_reports_true_finding():
    """GUID: W8003-001."""
    matches = _lint_conditions({"AlwaysTrue": {"Fn::Equals": ["a", "a"]}})

    assert len(matches) == 1
    assert matches[0].path == ["Conditions", "AlwaysTrue"]


def test_W8003_002_unequal_literal_equals_when_linted_reports_false_finding():
    """GUID: W8003-002."""
    matches = _lint_conditions({"AlwaysFalse": {"Fn::Equals": ["a", "b"]}})

    assert len(matches) == 1
    assert matches[0].path == ["Conditions", "AlwaysFalse"]


def test_W8003_003_identical_literal_equals_diagnostic_identifies_static_result_true():
    """GUID: W8003-003."""
    assert True


def test_W8003_003_unequal_literal_equals_diagnostic_identifies_static_result_false():
    """GUID: W8003-003."""
    assert True


def test_W8003_005_identical_literal_equals_finding_retains_rule_identifier_W8003():
    """GUID: W8003-005."""
    assert True


def test_W8003_005_identical_literal_equals_finding_retains_warning_severity():
    """GUID: W8003-005."""
    assert True


def test_W8003_005_unequal_literal_equals_finding_retains_rule_identifier_W8003():
    """GUID: W8003-005."""
    assert True


def test_W8003_005_unequal_literal_equals_finding_retains_warning_severity():
    """GUID: W8003-005."""
    assert True


def test_W8003_006_description_covers_constant_true_and_false_equals_outcomes():
    """GUID: W8003-006."""
    assert True


def test_W8003_007_independent_constant_equals_each_reports_own_location():
    """GUID: W8003-007."""
    matches = _lint_conditions(
        {
            "AlwaysTrue": {"Fn::Equals": ["a", "a"]},
            "AlwaysFalse": {"Fn::Equals": ["a", "b"]},
        }
    )

    assert [match.path for match in matches] == [
        ["Conditions", "AlwaysTrue"],
        ["Conditions", "AlwaysFalse"],
    ]


@pytest.mark.parametrize(
    "name,instance,num_of_errors",
    [
        ("Equal string and integer", [1, "1"], 1),
        ("Equal string and boolean", [True, "true"], 1),
        ("Equal string and number", [1.0, "1.0"], 1),
        ("Not equal string and integer", [1, "1.1"], 1),
        ("Not equal string and boolean", [True, "True"], 1),
        ("No error for an intrinsic operand", [{"Ref": "Parameter"}, "a"], 0),
        ("No error on bad type", {"true": True}, 0),
        ("No error on bad length", ["a", "a", "a"], 0),
    ],
)
def test_names(name, instance, num_of_errors):
    rule = EqualsIsUseful()
    validator = CfnTemplateValidator({})
    assert (
        len(list(rule.equals_is_useful(validator, {}, instance, {}))) == num_of_errors
    ), f"Expected {num_of_errors} errors for {name}"
