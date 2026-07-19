"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0

Verification coverage for IAM Condition operator recognition.
"""

# ruff: noqa: E501 -- canonical requirement IDs and scenario names stay readable

from pathlib import Path

import pytest

from cfnlint.context import Context
from cfnlint.decode import cfn_yaml
from cfnlint.helpers import FUNCTIONS
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


def _validate_identity_policy_with_functions(policy):
    validator = CfnTemplateValidator({}).evolve(context=Context(functions=FUNCTIONS))
    return list(
        IdentityPolicy().validate(
            validator=validator,
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


IAMCOND_009_010_PLACEHOLDER_REASON = (
    "Netzach placeholder: enable during Malkhut validation"
)


@pytest.mark.skip(reason=IAMCOND_009_010_PLACEHOLDER_REASON)
@pytest.mark.parametrize(
    "malformed_operator",
    [
        pytest.param("UnknownOperator", id="unknown"),
        pytest.param("ForAnyValues:StringEquals", id="incorrect-plural-qualifier"),
        pytest.param("ForAnyValue:StringEqual", id="misspelled-comparison"),
        pytest.param(" ForAnyValue:StringEquals", id="leading-extraneous-character"),
        pytest.param("ForAnyValue:StringEquals ", id="trailing-extraneous-character"),
        pytest.param("ForAnyValue:String-Equals", id="embedded-extraneous-character"),
    ],
)
def test_iamcond_009_given_unknown_unsupported_or_malformed_operator_when_e3510_validates_then_error_path_ends_at_that_operator(
    malformed_operator,
):
    policy = _policy_with_condition(
        {malformed_operator: {"example:key": ["value"]}}
    )

    errors = _validate_identity_policy(policy)

    assert [list(error.path) for error in errors] == [
        ["Statement", "Condition", malformed_operator]
    ]


@pytest.mark.skip(reason=IAMCOND_009_010_PLACEHOLDER_REASON)
@pytest.mark.parametrize("qualifier", ["ForAnyValue:", "ForAllValues:"])
@pytest.mark.parametrize(
    "invalid_value",
    [
        pytest.param("scalar", id="string"),
        pytest.param(True, id="boolean"),
        pytest.param(1, id="number"),
        pytest.param({"unexpected": "object"}, id="object"),
        pytest.param(None, id="null"),
    ],
)
def test_iamcond_010_given_set_qualified_condition_key_maps_to_non_array_when_e3510_validates_then_value_is_rejected_at_operator_and_key_path(
    qualifier, invalid_value
):
    operator = f"{qualifier}StringEquals"
    policy = _policy_with_condition({operator: {"example:key": invalid_value}})

    errors = _validate_identity_policy(policy)

    assert [list(error.path) for error in errors] == [
        ["Statement", "Condition", operator, "example:key"]
    ]


@pytest.mark.skip(reason=IAMCOND_009_010_PLACEHOLDER_REASON)
@pytest.mark.parametrize("qualifier", ["ForAnyValue:", "ForAllValues:"])
def test_iamcond_010_given_set_qualified_array_contains_non_string_compatible_elements_when_e3510_validates_then_each_is_rejected_at_policy_relative_array_path(
    qualifier,
):
    operator = f"{qualifier}StringEquals"
    values = ["valid", True, 1, None, {"unexpected": "object"}]
    policy = _policy_with_condition({operator: {"example:key": values}})

    errors = _validate_identity_policy(policy)

    assert [list(error.path) for error in errors] == [
        ["Statement", "Condition", operator, "example:key", index]
        for index in (1, 2, 3, 4)
    ]


@pytest.mark.skip(reason=IAMCOND_009_010_PLACEHOLDER_REASON)
@pytest.mark.parametrize("qualifier", ["ForAnyValue:", "ForAllValues:"])
def test_iamcond_010_given_each_set_condition_key_has_literal_strings_and_supported_cfn_string_expressions_when_object_policy_with_functions_is_validated_then_no_type_or_operator_errors(
    qualifier,
):
    operator = f"{qualifier}StringEquals"
    policy = _policy_with_condition(
        {
            operator: {
                "example:first": ["literal", {"Ref": "AWS::Region"}],
                "example:second": [
                    {"Fn::Sub": "prefix-${AWS::Partition}"},
                    "second-literal",
                ],
            }
        }
    )

    assert _validate_identity_policy_with_functions(policy) == []


@pytest.mark.skip(reason=IAMCOND_009_010_PLACEHOLDER_REASON)
def test_iamcond_009_given_malformed_operator_alongside_corrected_operator_when_e3510_validates_then_malformed_error_remains_and_corrected_operator_adds_no_error():
    malformed_operator = "ForAnyValues:StringEquals"
    corrected_operator = "ForAnyValue:StringEquals"
    policy = _policy_with_condition(
        {
            malformed_operator: {"example:malformed": ["value"]},
            corrected_operator: {"example:corrected": ["value"]},
        }
    )

    errors = _validate_identity_policy(policy)

    assert [list(error.path) for error in errors] == [
        ["Statement", "Condition", malformed_operator]
    ]
