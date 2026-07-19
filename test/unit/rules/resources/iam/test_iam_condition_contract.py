"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0

Verification coverage for the shared IAM Condition contract.

The parametrized node IDs preserve the rule family, operator or entry point,
input shape, and expected outcome for harness validation.
"""

from __future__ import annotations

import json

import pytest

from cfnlint.context import Context
from cfnlint.helpers import FUNCTIONS
from cfnlint.jsonschema import CfnTemplateValidator
from cfnlint.rules.resources.iam.IdentityPolicy import IdentityPolicy
from cfnlint.rules.resources.iam.ResourceEcrPolicy import ResourceEcrPolicy
from cfnlint.rules.resources.iam.ResourcePolicy import ResourcePolicy


RULE_CASES = (
    pytest.param(IdentityPolicy, "E3510", id="E3510-identity"),
    pytest.param(ResourcePolicy, "E3512", id="E3512-resource"),
    pytest.param(ResourceEcrPolicy, "E3513", id="E3513-ecr"),
)

# Every expansion of the eight ConditionValue patternProperties, plus the two
# explicit properties that use the same value schema.
_CONDITION_VALUE_BASES = (
    "IpAddress",
    "NotIpAddress",
    "ArnEquals",
    "ArnNotEquals",
    "ArnLike",
    "ArnNotLike",
    "DateEquals",
    "DateNotEquals",
    "NumberLessThan",
    "NumberGreaterThan",
    "NumberLessThanEquals",
    "NumberGreaterThanEquals",
    "NumberEquals",
    "NumberNotEquals",
    "StringEquals",
    "StringNotEquals",
    "StringEqualsIgnoreCase",
    "StringNotEqualsIgnoreCase",
    "StringLike",
    "StringNotLike",
)
CONDITION_VALUE_OPERATORS = (
    "BinaryEquals",
    "Bool",
    *(
        operator + suffix
        for operator in _CONDITION_VALUE_BASES
        for suffix in ("", "Exists")
    ),
)

# Every intended expansion of the sixteen set-qualified patternProperties.
_CONDITION_SET_BASES = tuple(
    operator for operator in _CONDITION_VALUE_BASES if not operator.endswith("Exists")
)
CONDITION_SET_VALUE_OPERATORS = tuple(
    f"{qualifier}:{operator}"
    for qualifier in ("ForAllValues", "ForAnyValues")
    for operator in _CONDITION_SET_BASES
)
ALL_CONDITION_OPERATORS = (
    *CONDITION_VALUE_OPERATORS,
    *CONDITION_SET_VALUE_OPERATORS,
    "Null",
)

OBJECT_OR_JSON_STRING_ENTRY_POINTS = (
    pytest.param(
        IdentityPolicy,
        "E3510",
        "Resources/AWS::IAM::Group/Properties/Policies/*/PolicyDocument",
        id="E3510-AWS_IAM_Group-PolicyDocument",
    ),
    pytest.param(
        IdentityPolicy,
        "E3510",
        "Resources/AWS::IAM::ManagedPolicy/Properties/PolicyDocument",
        id="E3510-AWS_IAM_ManagedPolicy-PolicyDocument",
    ),
    pytest.param(
        IdentityPolicy,
        "E3510",
        "Resources/AWS::IAM::Policy/Properties/PolicyDocument",
        id="E3510-AWS_IAM_Policy-PolicyDocument",
    ),
    pytest.param(
        IdentityPolicy,
        "E3510",
        "Resources/AWS::SSO::PermissionSet/Properties/InlinePolicy",
        id="E3510-AWS_SSO_PermissionSet-InlinePolicy",
    ),
    pytest.param(
        ResourcePolicy,
        "E3512",
        "Resources/AWS::KMS::Key/Properties/KeyPolicy",
        id="E3512-AWS_KMS_Key-KeyPolicy",
    ),
    pytest.param(
        ResourcePolicy,
        "E3512",
        "Resources/AWS::OpenSearchService::Domain/Properties/AccessPolicies",
        id="E3512-AWS_OpenSearchService_Domain-AccessPolicies",
    ),
    pytest.param(
        ResourcePolicy,
        "E3512",
        "Resources/AWS::S3::BucketPolicy/Properties/PolicyDocument",
        id="E3512-AWS_S3_BucketPolicy-PolicyDocument",
    ),
    pytest.param(
        ResourcePolicy,
        "E3512",
        "Resources/AWS::SNS::TopicPolicy/Properties/PolicyDocument",
        id="E3512-AWS_SNS_TopicPolicy-PolicyDocument",
    ),
    pytest.param(
        ResourcePolicy,
        "E3512",
        "Resources/AWS::SQS::QueuePolicy/Properties/PolicyDocument",
        id="E3512-AWS_SQS_QueuePolicy-PolicyDocument",
    ),
    pytest.param(
        ResourceEcrPolicy,
        "E3513",
        "Resources/AWS::ECR::Repository/Properties/RepositoryPolicyText",
        id="E3513-AWS_ECR_Repository-RepositoryPolicyText",
    ),
)

MISSING = object()


def _policy(rule_id: str, condition: object = MISSING) -> dict[str, object]:
    statement: dict[str, object] = {
        "Effect": "Allow",
        "Action": "*",
    }
    if rule_id != "E3513":
        statement["Resource"] = "*"
    if rule_id in ("E3512", "E3513"):
        statement["Principal"] = "*"
    if condition is not MISSING:
        statement["Condition"] = condition
    return {"Version": "2012-10-17", "Statement": [statement]}


def _errors(rule_class, policy: object, *, functions: bool = False):
    validator = CfnTemplateValidator()
    if functions:
        validator = validator.evolve(context=Context(functions=FUNCTIONS))
    return list(
        rule_class().validate(
            validator=validator,
            policy=policy,
            schema={},
            policy_type=None,
        )
    )


def _paths(errors) -> list[list[object]]:
    return [list(error.path) for error in errors]


def _assert_condition_error(errors, *tail: object) -> None:
    expected = ["Statement", 0, "Condition", *tail]
    paths = _paths(errors)
    assert any(path[: len(expected)] == expected for path in paths), errors


@pytest.mark.parametrize("rule_class,rule_id", RULE_CASES)
@pytest.mark.parametrize(
    "unknown_value",
    (
        pytest.param("value", id="scalar"),
        pytest.param(["value"], id="list"),
        pytest.param({"aws:SourceAccount": "123456789012"}, id="object"),
    ),
)
def test_IAMCOND_002_unknown_top_level_member_is_rejected_beneath_condition(
    rule_class, rule_id: str, unknown_value: object
) -> None:
    errors = _errors(rule_class, _policy(rule_id, {"UnknownOperator": unknown_value}))

    _assert_condition_error(errors, "UnknownOperator")


@pytest.mark.parametrize("rule_class,rule_id", RULE_CASES)
@pytest.mark.parametrize(
    "operator", (pytest.param(value, id=value) for value in ALL_CONDITION_OPERATORS)
)
@pytest.mark.parametrize(
    "operator_body",
    (
        pytest.param("aws:SourceAccount", id="scalar-body"),
        pytest.param(["aws:SourceAccount"], id="list-body"),
    ),
)
def test_IAMCOND_006_each_recognized_operator_rejects_a_non_object_body(
    rule_class, rule_id: str, operator: str, operator_body: object
) -> None:
    errors = _errors(rule_class, _policy(rule_id, {operator: operator_body}))

    _assert_condition_error(errors, operator)


@pytest.mark.parametrize("rule_class,rule_id", RULE_CASES)
@pytest.mark.parametrize(
    "operator",
    (pytest.param(value, id=value) for value in CONDITION_VALUE_OPERATORS),
)
@pytest.mark.parametrize(
    "context_value,accepted",
    (
        pytest.param("value", True, id="supported-string"),
        pytest.param(1, True, id="supported-number"),
        pytest.param(True, True, id="supported-boolean"),
        pytest.param(["one", "two"], True, id="supported-string-list"),
        pytest.param({"nested": "value"}, False, id="unsupported-object"),
        pytest.param(["one", 2], False, id="unsupported-non-string-list-item"),
    ),
)
def test_IAMCOND_007_condition_value_operators_preserve_context_value_shapes(
    rule_class, rule_id: str, operator: str, context_value: object, accepted: bool
) -> None:
    errors = _errors(
        rule_class,
        _policy(rule_id, {operator: {"aws:SourceAccount": context_value}}),
    )

    if accepted:
        assert errors == []
    else:
        _assert_condition_error(errors, operator, "aws:SourceAccount")


@pytest.mark.parametrize("rule_class,rule_id", RULE_CASES)
@pytest.mark.parametrize(
    "operator",
    (pytest.param(value, id=value) for value in CONDITION_SET_VALUE_OPERATORS),
)
@pytest.mark.parametrize(
    "context_value,accepted",
    (
        pytest.param(["one", "two"], True, id="supported-string-list"),
        pytest.param("one", False, id="unsupported-string"),
        pytest.param(1, False, id="unsupported-number"),
        pytest.param(True, False, id="unsupported-boolean"),
        pytest.param({"nested": "value"}, False, id="unsupported-object"),
        pytest.param(["one", 2], False, id="unsupported-non-string-list-item"),
    ),
)
def test_IAMCOND_007_set_operators_preserve_array_only_context_value_shapes(
    rule_class, rule_id: str, operator: str, context_value: object, accepted: bool
) -> None:
    errors = _errors(
        rule_class,
        _policy(rule_id, {operator: {"aws:SourceAccount": context_value}}),
    )

    if accepted:
        assert errors == []
    else:
        _assert_condition_error(errors, operator, "aws:SourceAccount")


@pytest.mark.parametrize("rule_class,rule_id", RULE_CASES)
@pytest.mark.parametrize(
    "context_value,accepted",
    (
        pytest.param("true", True, id="supported-true-string"),
        pytest.param("false", True, id="supported-false-string"),
        pytest.param(True, True, id="supported-boolean"),
        pytest.param(["true", False], True, id="supported-boolean-list"),
        pytest.param("not-boolean", False, id="unsupported-string"),
        pytest.param(1, False, id="unsupported-number"),
        pytest.param(["true", 1], False, id="unsupported-list-item"),
        pytest.param({"nested": True}, False, id="unsupported-object"),
    ),
)
def test_IAMCOND_007_null_operator_preserves_boolean_context_value_shapes(
    rule_class, rule_id: str, context_value: object, accepted: bool
) -> None:
    errors = _errors(
        rule_class,
        _policy(rule_id, {"Null": {"aws:SourceAccount": context_value}}),
    )

    if accepted:
        assert errors == []
    else:
        _assert_condition_error(errors, "Null", "aws:SourceAccount")


@pytest.mark.parametrize("rule_class,rule_id", RULE_CASES)
def test_IAMCOND_008_recognized_well_structured_condition_remains_valid_per_family(
    rule_class, rule_id: str
) -> None:
    errors = _errors(
        rule_class,
        _policy(rule_id, {"StringEquals": {"aws:SourceAccount": "123456789012"}}),
    )

    assert errors == []


@pytest.mark.parametrize("rule_class,rule_id", RULE_CASES)
def test_IAMCOND_009_supported_intrinsic_in_place_of_condition_operator_is_not_unknown(
    rule_class, rule_id: str
) -> None:
    condition = {
        "Fn::If": [
            "UseSourceAccount",
            {"StringEquals": {"aws:SourceAccount": {"Ref": "AWS::AccountId"}}},
            {"Ref": "AWS::NoValue"},
        ]
    }
    errors = _errors(rule_class, _policy(rule_id, condition), functions=True)

    assert ["Statement", 0, "Condition", "Fn::If"] not in _paths(errors)


@pytest.mark.parametrize("rule_class,rule_id", RULE_CASES)
def test_IAMCOND_009_supported_intrinsics_keep_existing_embedded_policy_outcomes(
    rule_class, rule_id: str
) -> None:
    policy = _policy(
        rule_id,
        {"StringEquals": {"aws:SourceAccount": {"Ref": "AWS::AccountId"}}},
    )
    statement = policy["Statement"][0]
    assert isinstance(statement, dict)
    statement["Action"] = {"Fn::If": ["UseAction", "s3:GetObject", "s3:ListBucket"]}
    if "Resource" in statement:
        statement["Resource"] = {"Fn::Sub": "arn:${AWS::Partition}:s3:::example"}

    assert _errors(rule_class, policy, functions=True) == []


@pytest.mark.parametrize(
    "rule_class,rule_id,entry_point", OBJECT_OR_JSON_STRING_ENTRY_POINTS
)
@pytest.mark.parametrize(
    "condition,expected_valid",
    (
        pytest.param({"UnknownOperator": "value"}, False, id="missing-operator"),
        pytest.param(
            {"StringEquals": {"aws:SourceAccount": "123456789012"}},
            True,
            id="valid-condition",
        ),
    ),
)
def test_IAMCOND_010_object_and_json_string_representations_have_equivalent_outcomes(
    rule_class,
    rule_id: str,
    entry_point: str,
    condition: object,
    expected_valid: bool,
) -> None:
    rule = rule_class()
    assert entry_point in rule.keywords
    object_policy = _policy(rule_id, condition)
    object_errors = _errors(rule_class, object_policy)
    string_errors = _errors(rule_class, json.dumps(object_policy))

    assert _paths(object_errors) == _paths(string_errors)
    if expected_valid:
        assert object_errors == string_errors == []
    else:
        _assert_condition_error(object_errors, "UnknownOperator")
        _assert_condition_error(string_errors, "UnknownOperator")


@pytest.mark.parametrize("rule_class,rule_id", RULE_CASES)
def test_IAMCOND_011_statement_without_optional_condition_has_no_condition_finding(
    rule_class, rule_id: str
) -> None:
    errors = _errors(rule_class, _policy(rule_id))

    assert not any("Condition" in path for path in _paths(errors))


@pytest.mark.parametrize("rule_class,rule_id", RULE_CASES)
def test_IAMCOND_012_multiple_operators_and_context_keys_remain_accepted(
    rule_class, rule_id: str
) -> None:
    condition = {
        "StringEquals": {
            "aws:SourceAccount": "123456789012",
            "aws:PrincipalOrgID": "o-example",
        },
        "ArnLike": {
            "aws:SourceArn": [
                "arn:aws:s3:::first-example",
                "arn:aws:s3:::second-example",
            ]
        },
    }

    assert _errors(rule_class, _policy(rule_id, condition)) == []


@pytest.mark.parametrize("rule_class,rule_id", RULE_CASES)
@pytest.mark.parametrize(
    "independent_defect,expected_tail",
    (
        pytest.param("version", ["Version"], id="invalid-version"),
        pytest.param("statement", ["Statement", 1], id="invalid-statement"),
        pytest.param("effect", ["Statement", 0, "Effect"], id="invalid-effect"),
        pytest.param("action", ["Statement", 0, "Action"], id="invalid-action"),
        pytest.param("resource", ["Statement", 0, "Resource"], id="invalid-resource"),
        pytest.param(
            "unsupported-property",
            ["Statement", 0, "UnsupportedProperty"],
            id="unsupported-property",
        ),
    ),
)
def test_IAMCOND_013_condition_finding_does_not_suppress_independent_findings(
    rule_class, rule_id: str, independent_defect: str, expected_tail: list[object]
) -> None:
    policy = _policy(rule_id, {"UnknownOperator": "value"})
    statement = policy["Statement"][0]
    assert isinstance(statement, dict)
    if independent_defect == "version":
        policy["Version"] = "2012-10-18"
    elif independent_defect == "statement":
        policy["Statement"].append("not-an-object")
    elif independent_defect == "effect":
        statement["Effect"] = "NotAllow"
    elif independent_defect == "action":
        statement["Action"] = {"not": "an-action"}
    elif independent_defect == "resource":
        statement["Resource"] = {"not": "a-resource"}
    else:
        statement["UnsupportedProperty"] = True

    errors = _errors(rule_class, policy)

    _assert_condition_error(errors, "UnknownOperator")
    assert expected_tail in _paths(errors), errors


@pytest.mark.parametrize(
    "rule_class,rule_id",
    (
        pytest.param(ResourcePolicy, "E3512", id="E3512-resource"),
        pytest.param(ResourceEcrPolicy, "E3513", id="E3513-ecr"),
    ),
)
def test_IAMCOND_013_condition_finding_does_not_suppress_invalid_principal(
    rule_class, rule_id: str
) -> None:
    policy = _policy(rule_id, {"UnknownOperator": "value"})
    policy["Statement"][0]["Principal"] = {"AWS": "not-an-arn"}
    errors = _errors(rule_class, policy)

    _assert_condition_error(errors, "UnknownOperator")
    assert ["Statement", 0, "Principal", "AWS"] in _paths(errors), errors
