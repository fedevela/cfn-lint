"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0

Verification coverage for IAMCOND-006 E3510 entry-point continuity.
"""

# ruff: noqa: E501 -- canonical requirement IDs and scenario names stay readable

from __future__ import annotations

import json
from copy import deepcopy

import pytest

from cfnlint import lint
from cfnlint.config import ManualArgs


def _policy_document(operator="StringEqualsIfExists"):
    condition_value = ["value"] if operator.startswith("For") else "value"
    return {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "s3:GetObject",
            "Resource": "*",
            "Condition": {operator: {"example:key": condition_value}},
        },
    }


def _group(policy):
    return {
        "Type": "AWS::IAM::Group",
        "Properties": {
            "Policies": [{"PolicyName": "group-policy", "PolicyDocument": policy}]
        },
    }


def _managed_policy(policy):
    return {
        "Type": "AWS::IAM::ManagedPolicy",
        "Properties": {"PolicyDocument": policy},
    }


def _standalone_policy(policy):
    return {
        "Type": "AWS::IAM::Policy",
        "Properties": {
            "PolicyName": "standalone-policy",
            "Groups": ["example-group"],
            "PolicyDocument": policy,
        },
    }


def _role(policy):
    return {
        "Type": "AWS::IAM::Role",
        "Properties": {
            "AssumeRolePolicyDocument": _policy_document(),
            "Policies": [{"PolicyName": "role-policy", "PolicyDocument": policy}],
        },
    }


def _user(policy):
    return {
        "Type": "AWS::IAM::User",
        "Properties": {
            "Policies": [{"PolicyName": "user-policy", "PolicyDocument": policy}]
        },
    }


def _permission_set(policy):
    return {
        "Type": "AWS::SSO::PermissionSet",
        "Properties": {
            "InstanceArn": "arn:aws:sso:::instance/ssoins-0123456789abcdef",
            "Name": "example-permission-set",
            "InlinePolicy": policy,
        },
    }


ENTRY_POINTS = [
    pytest.param(
        _group,
        ["Properties", "Policies", 0, "PolicyDocument"],
        id="group-inline-policy",
    ),
    pytest.param(
        _managed_policy,
        ["Properties", "PolicyDocument"],
        id="managed-policy",
    ),
    pytest.param(
        _standalone_policy,
        ["Properties", "PolicyDocument"],
        id="standalone-inline-policy",
    ),
    pytest.param(
        _role,
        ["Properties", "Policies", 0, "PolicyDocument"],
        id="role-inline-policy",
    ),
    pytest.param(
        _user,
        ["Properties", "Policies", 0, "PolicyDocument"],
        id="user-inline-policy",
    ),
    pytest.param(
        _permission_set,
        ["Properties", "InlinePolicy"],
        id="sso-permission-set-inline-policy",
    ),
]


def _lint_e3510(resources):
    template = {"AWSTemplateFormatVersion": "2010-09-09", "Resources": resources}
    return lint(
        json.dumps(template),
        config=ManualArgs(include_checks=["E3510"]),
    )


@pytest.mark.parametrize("resource_factory,_policy_path", ENTRY_POINTS)
def test_iamcond_006_given_equivalent_valid_corrected_condition_when_each_e3510_owned_resource_type_is_linted_then_no_unsupported_operator_error(
    resource_factory, _policy_path
):
    matches = _lint_e3510({"EntryPoint": resource_factory(_policy_document())})

    assert matches == []


@pytest.mark.parametrize("resource_factory", [_group, _role, _user])
@pytest.mark.parametrize("corrected_policy_index", [0, 1])
def test_iamcond_006_given_group_role_or_user_with_multiple_policy_entries_when_corrected_operator_occurs_at_any_wildcard_location_then_e3510_accepts_that_entry(
    resource_factory, corrected_policy_index
):
    resource = resource_factory(_policy_document())
    policies = [
        {"PolicyName": "first-policy", "PolicyDocument": _policy_document()},
        {"PolicyName": "second-policy", "PolicyDocument": _policy_document()},
    ]
    policies[corrected_policy_index]["PolicyDocument"] = _policy_document(
        "ForAnyValue:StringEquals"
    )
    resource["Properties"]["Policies"] = policies

    assert _lint_e3510({"WildcardOwner": resource}) == []


@pytest.mark.parametrize("resource_factory,policy_path", ENTRY_POINTS)
def test_iamcond_006_given_genuine_condition_violation_at_each_owned_entry_point_when_template_is_linted_then_match_remains_e3510_with_full_owning_policy_path(
    resource_factory, policy_path
):
    invalid_operator = "UnsupportedOperator"
    matches = _lint_e3510(
        {"InvalidEntryPoint": resource_factory(_policy_document(invalid_operator))}
    )

    assert [match.rule.id for match in matches] == ["E3510"]
    assert [list(match.path) for match in matches] == [
        [
            "Resources",
            "InvalidEntryPoint",
            *policy_path,
            "Statement",
            "Condition",
            invalid_operator,
        ]
    ]


def test_iamcond_006_given_one_valid_corrected_condition_per_owned_resource_type_when_all_are_linted_together_then_entry_point_validation_is_independent_and_unchanged():
    operators_and_factories = [
        ("StringEqualsIfExists", _group),
        ("ForAnyValue:StringEquals", _managed_policy),
        ("ForAllValues:StringEquals", _standalone_policy),
        ("ArnLikeIfExists", _role),
        ("ForAnyValue:ArnLike", _user),
        ("ForAllValues:StringLike", _permission_set),
    ]
    resources = {
        f"EntryPoint{index}": factory(_policy_document(operator))
        for index, (operator, factory) in enumerate(operators_and_factories)
    }

    combined_matches = _lint_e3510(deepcopy(resources))
    isolated_matches = [
        _lint_e3510({logical_id: deepcopy(resource)})
        for logical_id, resource in resources.items()
    ]

    assert combined_matches == []
    assert isolated_matches == [[] for _resource in resources]
