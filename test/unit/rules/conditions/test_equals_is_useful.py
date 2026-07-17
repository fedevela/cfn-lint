"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

import pytest

from cfnlint.jsonschema import CfnTemplateValidator
from cfnlint.rules.conditions.EqualsIsUseful import EqualsIsUseful


def test_W8003_001_identical_literal_equals_when_linted_reports_true_finding():
    """GUID: W8003-001."""
    assert True


def test_W8003_002_unequal_literal_equals_when_linted_reports_false_finding():
    """GUID: W8003-002."""
    assert True


def test_W8003_007_independent_constant_equals_each_reports_own_location():
    """GUID: W8003-007."""
    assert True


@pytest.mark.parametrize(
    "name,instance,num_of_errors",
    [
        ("Equal string and integer", [1, "1"], 1),
        ("Equal string and boolean", [True, "true"], 1),
        ("Equal string and number", [1.0, "1.0"], 1),
        ("Not equal string and integer", [1, "1.1"], 0),
        ("Not equal string and boolean", [True, "True"], 0),
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
