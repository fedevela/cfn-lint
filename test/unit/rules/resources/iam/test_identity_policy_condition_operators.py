"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0

Verification coverage for IAM Condition operator recognition.
"""

# ruff: noqa: E501 -- canonical requirement IDs and scenario names stay readable

from pathlib import Path

import pytest

from cfnlint.decode import cfn_yaml
from cfnlint.jsonschema import CfnTemplateValidator
from cfnlint.rules.resources.iam.IdentityPolicy import IdentityPolicy


PARALLELCLUSTER_FIXTURE = Path(
    "test/fixtures/templates/issues/issue_3777_parallelcluster_condition_operators.yaml"
)


def _policy_with_condition(condition):
    return {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "*",
            "Resource": "*",
            "Condition": condition,
        },
    }


def _condition_values():
    return {
        "example:scalar": "value",
        "example:array": ["value", "second-value"],
    }


def _validate_identity_policy(policy):
    return list(
        IdentityPolicy().validate(
            validator=CfnTemplateValidator(),
            policy=policy,
            schema={},
            policy_type=None,
        )
    )


@pytest.mark.parametrize("value", ["value", ["value", "second-value"]])
def test_iamcond_001_given_string_or_string_array_when_string_equals_if_exists_then_e3510_accepts(
    value,
):
    policy = _policy_with_condition(
        {"StringEqualsIfExists": {"example:key": value}}
    )

    assert _validate_identity_policy(policy) == []


def test_iamcond_002_given_string_array_when_for_any_value_string_equals_then_e3510_accepts():
    policy = _policy_with_condition(
        {"ForAnyValue:StringEquals": {"example:key": ["value", "second-value"]}}
    )

    assert _validate_identity_policy(policy) == []


def test_iamcond_003_given_string_array_when_for_all_values_string_equals_then_e3510_accepts():
    policy = _policy_with_condition(
        {"ForAllValues:StringEquals": {"example:key": ["value", "second-value"]}}
    )

    assert _validate_identity_policy(policy) == []


SET_QUALIFIED_OPERATORS = [
    "IpAddress",
    "NotIpAddress",
    "ArnEquals",
    "ArnNotEquals",
    "ArnLike",
    "ArnNotLike",
    "DateEquals",
    "DateNotEquals",
    "NumericLessThan",
    "NumericLessThanEquals",
    "NumericGreaterThan",
    "NumericGreaterThanEquals",
    "NumericEquals",
    "NumericNotEquals",
    "StringEquals",
    "StringNotEquals",
    "StringEqualsIgnoreCase",
    "StringNotEqualsIgnoreCase",
    "StringLike",
    "StringNotLike",
]


@pytest.mark.parametrize(
    "qualifier,operator",
    [
        pytest.param(qualifier, operator, id=f"{qualifier}{operator}")
        for qualifier in ("ForAnyValue:", "ForAllValues:")
        for operator in SET_QUALIFIED_OPERATORS
    ],
)
def test_iamcond_004_given_supported_comparison_family_when_correct_set_qualifier_and_array_values_then_shared_condition_accepts(
    qualifier, operator
):
    policy = _policy_with_condition(
        {f"{qualifier}{operator}": {"example:key": ["value", "second-value"]}}
    )

    assert _validate_identity_policy(policy) == []


IF_EXISTS_OPERATORS = [
    "IpAddressIfExists",
    "NotIpAddressIfExists",
    "ArnEqualsIfExists",
    "ArnNotEqualsIfExists",
    "ArnLikeIfExists",
    "ArnNotLikeIfExists",
    "DateEqualsIfExists",
    "DateNotEqualsIfExists",
    "NumericLessThanIfExists",
    "NumericLessThanEqualsIfExists",
    "NumericGreaterThanIfExists",
    "NumericGreaterThanEqualsIfExists",
    "NumericEqualsIfExists",
    "NumericNotEqualsIfExists",
    "StringEqualsIfExists",
    "StringNotEqualsIfExists",
    "StringEqualsIgnoreCaseIfExists",
    "StringNotEqualsIgnoreCaseIfExists",
    "StringLikeIfExists",
    "StringNotLikeIfExists",
]


@pytest.mark.parametrize(
    "operator",
    [pytest.param(operator, id=operator) for operator in IF_EXISTS_OPERATORS],
)
def test_iamcond_005_given_non_set_comparison_family_when_if_exists_with_established_values_then_shared_condition_accepts(
    operator,
):
    policy = _policy_with_condition({operator: _condition_values()})

    assert _validate_identity_policy(policy) == []


def test_iamcond_001_002_003_given_parallelcluster_reproduction_when_e3510_validates_both_if_exists_and_set_qualified_occurrences_then_no_condition_operator_errors():
    template = cfn_yaml.load(str(PARALLELCLUSTER_FIXTURE))
    policies = [
        resource["Properties"]["PolicyDocument"]
        for resource in template["Resources"].values()
    ]

    errors = [error for policy in policies for error in _validate_identity_policy(policy)]

    assert errors == []
