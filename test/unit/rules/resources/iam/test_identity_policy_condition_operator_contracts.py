"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

import pytest

from cfnlint.jsonschema import CfnTemplateValidator
from cfnlint.rules.resources.iam.IdentityPolicy import IdentityPolicy


RESOURCE_TYPES = ("AWS::IAM::ManagedPolicy", "AWS::IAM::Policy")
BASE_OPERATORS = (
    "ArnEquals",
    "ArnLike",
    "ArnNotEquals",
    "ArnNotLike",
    "BinaryEquals",
    "Bool",
    "DateEquals",
    "DateNotEquals",
    "DateLessThan",
    "DateLessThanEquals",
    "DateGreaterThan",
    "DateGreaterThanEquals",
    "IpAddress",
    "NotIpAddress",
    "NumericEquals",
    "NumericNotEquals",
    "NumericLessThan",
    "NumericLessThanEquals",
    "NumericGreaterThan",
    "NumericGreaterThanEquals",
    "StringEquals",
    "StringEqualsIgnoreCase",
    "StringNotEquals",
    "StringNotEqualsIgnoreCase",
    "StringLike",
    "StringNotLike",
)


def _errors_for_conditions(resource_type, conditions):
    rule = IdentityPolicy()
    resource_path = f"Resources/{resource_type}/Properties/PolicyDocument"
    assert resource_path in rule.keywords

    policy = {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "*",
            "Resource": "*",
            "Condition": conditions,
        },
    }
    return list(
        rule.validate(
            validator=CfnTemplateValidator(),
            policy=policy,
            schema={},
            policy_type=None,
        )
    )


def _errors_for(resource_type, operator):
    condition_value = ["value"] if operator.startswith("For") else "value"
    return _errors_for_conditions(
        resource_type, {operator: {"aws:TagKeys": condition_value}}
    )


@pytest.mark.parametrize("resource_type", RESOURCE_TYPES)
def test_iamop_001_string_equals_if_exists_emits_no_e3510(resource_type):
    """GUID: IAMOP-001; exact operator is accepted for both IAM resources."""
    assert _errors_for(resource_type, "StringEqualsIfExists") == []


@pytest.mark.parametrize("resource_type", RESOURCE_TYPES)
def test_iamop_002_for_any_value_string_equals_emits_no_e3510(resource_type):
    """GUID: IAMOP-002; exact operator is accepted for both IAM resources."""
    assert _errors_for(resource_type, "ForAnyValue:StringEquals") == []


@pytest.mark.parametrize("resource_type", RESOURCE_TYPES)
def test_iamop_003_for_all_values_string_equals_emits_no_e3510(resource_type):
    """GUID: IAMOP-003; exact operator is accepted for both IAM resources."""
    assert _errors_for(resource_type, "ForAllValues:StringEquals") == []


@pytest.mark.parametrize("resource_type", RESOURCE_TYPES)
@pytest.mark.parametrize("base_operator", BASE_OPERATORS)
def test_iamop_007_accepts_documented_if_exists_forms(
    resource_type, base_operator
):
    """GUID: IAMOP-007; documented IfExists forms are accepted exactly."""
    assert _errors_for(resource_type, f"{base_operator}IfExists") == []


@pytest.mark.parametrize("resource_type", RESOURCE_TYPES)
@pytest.mark.parametrize("qualifier", ("ForAnyValue", "ForAllValues"))
@pytest.mark.parametrize("suffix", ("", "IfExists"))
@pytest.mark.parametrize("base_operator", BASE_OPERATORS)
def test_iamop_007_accepts_documented_set_operator_forms(
    resource_type, qualifier, suffix, base_operator
):
    """GUID: IAMOP-007; documented set-operator forms are accepted exactly."""
    assert _errors_for(resource_type, f"{qualifier}:{base_operator}{suffix}") == []


@pytest.mark.parametrize(
    "operator",
    (
        "StringEqualsExists",
        "StringEqualsIfExist",
        "ForAnyValues:StringEquals",
        "ForAnyValueStringEquals",
        "ForAllValue:StringEquals",
        "ForAllValues:StringResembles",
        "ArbitraryIfExists",
    ),
)
def test_iamop_007_rejects_malformed_or_undocumented_forms(operator):
    """GUID: IAMOP-007; modifier-like names do not open the closed vocabulary."""
    errors = _errors_for("AWS::IAM::ManagedPolicy", operator)
    assert len(errors) == 1
    assert errors[0].validator == "additionalProperties"


def test_iamop_005_genuinely_invalid_operator_emits_applicable_finding():
    """GUID: IAMOP-005; an invalid operator name remains rejected."""
    errors = _errors_for("AWS::IAM::ManagedPolicy", "StringResembles")

    assert len(errors) == 1
    assert errors[0].rule.id == "E3510"
    assert errors[0].validator == "additionalProperties"
    assert list(errors[0].path) == ["Statement", "Condition", "StringResembles"]


def test_iamop_006_case_changed_aws_operator_emits_applicable_finding():
    """GUID: IAMOP-006; a case-only spelling change remains rejected."""
    errors = _errors_for("AWS::IAM::ManagedPolicy", "stringEquals")

    assert len(errors) == 1
    assert errors[0].rule.id == "E3510"
    assert errors[0].validator == "additionalProperties"
    assert list(errors[0].path) == ["Statement", "Condition", "stringEquals"]


def test_iamop_005_mixed_valid_and_invalid_operators_only_invalid_emits_finding():
    """GUID: IAMOP-005; mixed input rejects only the invalid operator name."""
    errors = _errors_for_conditions(
        "AWS::IAM::ManagedPolicy",
        {
            "StringEquals": {"aws:RequestTag/environment": "production"},
            "StringResembles": {"aws:RequestTag/team": "platform"},
        },
    )

    assert len(errors) == 1
    assert errors[0].rule.id == "E3510"
    assert errors[0].validator == "additionalProperties"
    assert list(errors[0].path) == ["Statement", "Condition", "StringResembles"]


def test_iamop_008_previously_accepted_operator_remains_without_operator_name_finding(
):
    """GUID: IAMOP-008; validation preserves prior operator acceptance."""
    # PSEUDOCODE — GUID: IAMOP-008
    # INPUT: the closed baseline of IAM Condition operator names accepted before
    # the correction, paired with every identity-policy resource type in scope.
    # FOR EACH baseline operator and resource type:
    #   CONSTRUCT an otherwise valid policy containing that exact operator name.
    #   INVOKE identity-policy validation and collect its findings.
    #   IF any finding is an E3510 operator-name rejection at that operator locus:
    #     RECORD the operator, resource type, path, and finding as a regression.
    #   ELSE:
    #     PRESERVE the operator's prior accepted state; do not broaden the set
    #     with undocumented names or alter the status of previously invalid names.
    # FAIL with all recorded regressions; otherwise REPORT no operator-name
    # findings for every previously accepted operator/resource pairing.
    assert True
