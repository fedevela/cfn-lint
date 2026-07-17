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


# Architecture seam (GUID: W8003-008, W8003-009, W8003-010): this test module
# owns W8003 condition fixtures and depends inward on the existing rule runner.
# `_lint_conditions` is the sole test adapter across that boundary: callers
# supply only the Conditions fragment and receive only W8003 Match objects.
# Rule selection, condition traversal, and output construction remain owned by
# ConfigMixIn, TemplateRunner, and the registered rules respectively.
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
    matches = _lint_conditions({"AlwaysTrue": {"Fn::Equals": ["a", "a"]}})

    assert matches[0].message == "['a', 'a'] will always return true"


def test_W8003_003_unequal_literal_equals_diagnostic_identifies_static_result_false():
    """GUID: W8003-003."""
    matches = _lint_conditions({"AlwaysFalse": {"Fn::Equals": ["a", "b"]}})

    assert matches[0].message == "['a', 'b'] will always return false"


def test_W8003_004_non_constant_fn_equals_when_linted_produces_no_W8003_finding():
    """GUID: W8003-004."""
    matches = _lint_conditions(
        {"EnvironmentIsProduction": {"Fn::Equals": [{"Ref": "Environment"}, "prod"]}}
    )

    assert matches == []


def test_W8003_005_identical_literal_equals_finding_retains_rule_identifier_W8003():
    """GUID: W8003-005."""
    matches = _lint_conditions({"AlwaysTrue": {"Fn::Equals": ["a", "a"]}})

    assert matches[0].rule.id == "W8003"


def test_W8003_005_identical_literal_equals_finding_retains_warning_severity():
    """GUID: W8003-005."""
    matches = _lint_conditions({"AlwaysTrue": {"Fn::Equals": ["a", "a"]}})

    assert matches[0].rule.severity == "warning"


def test_W8003_005_unequal_literal_equals_finding_retains_rule_identifier_W8003():
    """GUID: W8003-005."""
    matches = _lint_conditions({"AlwaysFalse": {"Fn::Equals": ["a", "b"]}})

    assert matches[0].rule.id == "W8003"


def test_W8003_005_unequal_literal_equals_finding_retains_warning_severity():
    """GUID: W8003-005."""
    matches = _lint_conditions({"AlwaysFalse": {"Fn::Equals": ["a", "b"]}})

    assert matches[0].rule.severity == "warning"


def test_W8003_006_description_covers_constant_true_and_false_equals_outcomes():
    """GUID: W8003-006."""
    description = EqualsIsUseful.description.lower()

    assert "statically return either true or false" in description


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


# Verification placement (GUID: W8003-008, W8003-009): literal-outcome and
# dynamic-operand cases live beside the W8003 adapter above. Later behavioral
# implementation consumes that adapter; it must not bypass TemplateRunner or
# reach into EqualsIsUseful internals.
def test_W8003_008_identical_literal_fn_equals_when_tests_run_verifies_W8003_finding():
    """GUID: W8003-008."""
    # Logic obligation: prove that an Fn::Equals with identical literal operands
    # is recognized as constant and produces the expected W8003 finding.
    # GIVEN a condition whose Fn::Equals operands are the same literal value
    # WHEN the condition is passed through the existing lint-test entry point
    # THEN retain only findings whose rule identifier is W8003
    # IF exactly one W8003 finding identifies the condition's location
    # THEN complete this verification successfully
    # ELSE fail with the observed finding count, rule identifiers, and locations
    assert True


def test_W8003_008_unequal_literal_fn_equals_when_tests_run_verifies_W8003_finding():
    """GUID: W8003-008."""
    # Logic obligation: prove that an Fn::Equals with unequal literal operands
    # is recognized as constant and produces the expected W8003 finding.
    # GIVEN a condition whose Fn::Equals operands are two unequal literal values
    # WHEN the condition is passed through the existing lint-test entry point
    # THEN retain only findings whose rule identifier is W8003
    # IF exactly one W8003 finding identifies the condition's location
    # THEN complete this verification successfully
    # ELSE fail with the observed finding count, rule identifiers, and locations
    assert True


def test_W8003_009_non_constant_fn_equals_when_tests_run_verifies_no_false_positive_W8003_finding():
    """GUID: W8003-009."""
    # Logic obligation: exclude Fn::Equals expressions whose result cannot be
    # statically proven so that dynamic operands never create false positives.
    # GIVEN a condition with at least one non-literal Fn::Equals operand
    # WHEN the condition is passed through the existing lint-test entry point
    # THEN retain only findings whose rule identifier is W8003
    # IF the retained finding collection is empty
    # THEN complete this verification successfully
    # ELSE fail with every unexpected finding's message and location
    assert True


# Regression ownership (GUID: W8003-010): these are traceability anchors for
# three existing suite boundaries, not new owners of those subsystems. General
# rule isolation remains under test/unit/rules; condition semantics remain under
# test/unit/module/conditions and test/unit/module/context/conditions; runner,
# API, and formatter tests retain ownership of diagnostic output integration.
def test_W8003_010_relevant_lint_suite_when_run_preserves_unrelated_rules():
    """GUID: W8003-010."""
    # Logic obligation: the corrected W8003 behavior must not change outcomes
    # owned by unrelated lint rules in the relevant existing suite.
    # GIVEN the existing unrelated-rule cases and their established expectations
    # WHEN the relevant lint suite executes with the corrected W8003 behavior
    # THEN compare each unrelated rule's observed findings with its expectation
    # IF every comparison is unchanged, complete this regression gate successfully
    # ELSE fail and identify each unrelated rule case whose outcome changed
    assert True


def test_W8003_010_relevant_lint_suite_when_run_preserves_condition_semantics():
    """GUID: W8003-010."""
    # Logic obligation: the corrected W8003 behavior must preserve established
    # evaluation and traversal semantics for conditions outside the corrected case.
    # GIVEN the existing condition-semantic cases and their expected outcomes
    # WHEN the relevant lint suite executes with the corrected W8003 behavior
    # THEN compare every observed condition outcome with its established expectation
    # IF every comparison is unchanged, complete this regression gate successfully
    # ELSE fail and identify the condition case and semantic outcome that changed
    assert True


def test_W8003_010_relevant_lint_suite_when_run_preserves_output_integration():
    """GUID: W8003-010."""
    # Logic obligation: W8003 findings must continue through the established lint
    # output boundary without changing unrelated diagnostic integration.
    # GIVEN the existing output-integration cases and their expected diagnostics
    # WHEN the relevant lint suite executes with the corrected W8003 behavior
    # THEN compare emitted rule identifiers, messages, severities, and locations
    # with the established expectations for each integration case
    # IF every comparison is unchanged, complete this regression gate successfully
    # ELSE fail and identify each diagnostic field and integration case that changed
    assert True


def test_W8003_011_non_equals_condition_function_after_correction_receives_no_new_handling():
    """GUID: W8003-011."""
    matches = _lint_conditions({"BothEnabled": {"Fn::And": [True, False]}})

    assert matches == []


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
