"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

import json
from collections import deque
from textwrap import indent

import pytest

from cfnlint.api import lint
from cfnlint.rules.resources.properties.StringLength import StringLength


MANAGED_POLICY_DOCUMENT_PATH = deque(
    [
        "Resources",
        "AWS::IAM::ManagedPolicy",
        "Properties",
        "PolicyDocument",
    ]
)
POLICY_DOCUMENT_SCHEMA = {"type": ["object", "string"]}
MAX_MANAGED_POLICY_SIZE = 6144
MANAGED_POLICY_WHITESPACE = str.maketrans("", "", " \t\r\n")

# The actions are those required by the AWS Load Balancer Controller policy. A
# wide JSON indentation preserves the reported block-scalar failure mode: the
# YAML value is over the provider-schema maxLength while the IAM quota length,
# which excludes JSON whitespace, remains within the limit.
AWS_LOAD_BALANCER_CONTROLLER_ACTIONS = [
    "iam:CreateServiceLinkedRole",
    "ec2:DescribeAccountAttributes",
    "ec2:DescribeAddresses",
    "ec2:DescribeAvailabilityZones",
    "ec2:DescribeInternetGateways",
    "ec2:DescribeVpcs",
    "ec2:DescribeVpcPeeringConnections",
    "ec2:DescribeSubnets",
    "ec2:DescribeSecurityGroups",
    "ec2:DescribeInstances",
    "ec2:DescribeNetworkInterfaces",
    "ec2:DescribeTags",
    "ec2:GetCoipPoolUsage",
    "ec2:DescribeCoipPools",
    "ec2:GetSecurityGroupsForVpc",
    "elasticloadbalancing:DescribeLoadBalancers",
    "elasticloadbalancing:DescribeLoadBalancerAttributes",
    "elasticloadbalancing:DescribeListeners",
    "elasticloadbalancing:DescribeListenerCertificates",
    "elasticloadbalancing:DescribeSSLPolicies",
    "elasticloadbalancing:DescribeRules",
    "elasticloadbalancing:DescribeTargetGroups",
    "elasticloadbalancing:DescribeTargetGroupAttributes",
    "elasticloadbalancing:DescribeTargetHealth",
    "elasticloadbalancing:DescribeTags",
    "elasticloadbalancing:DescribeTrustStores",
    "elasticloadbalancing:DescribeListenerAttributes",
    "elasticloadbalancing:DescribeCapacityReservation",
    "cognito-idp:DescribeUserPoolClient",
    "acm:ListCertificates",
    "acm:DescribeCertificate",
    "iam:ListServerCertificates",
    "iam:GetServerCertificate",
    "waf-regional:GetWebACL",
    "waf-regional:GetWebACLForResource",
    "waf-regional:AssociateWebACL",
    "waf-regional:DisassociateWebACL",
    "wafv2:GetWebACL",
    "wafv2:GetWebACLForResource",
    "wafv2:AssociateWebACL",
    "wafv2:DisassociateWebACL",
    "shield:GetSubscriptionState",
    "shield:DescribeProtection",
    "shield:CreateProtection",
    "shield:DeleteProtection",
    "ec2:AuthorizeSecurityGroupIngress",
    "ec2:RevokeSecurityGroupIngress",
    "ec2:CreateSecurityGroup",
    "ec2:CreateTags",
    "ec2:DeleteTags",
    "ec2:DeleteSecurityGroup",
    "elasticloadbalancing:CreateLoadBalancer",
    "elasticloadbalancing:CreateTargetGroup",
    "elasticloadbalancing:CreateListener",
    "elasticloadbalancing:DeleteListener",
    "elasticloadbalancing:CreateRule",
    "elasticloadbalancing:DeleteRule",
    "elasticloadbalancing:AddTags",
    "elasticloadbalancing:RemoveTags",
    "elasticloadbalancing:ModifyLoadBalancerAttributes",
    "elasticloadbalancing:SetIpAddressType",
    "elasticloadbalancing:SetSecurityGroups",
    "elasticloadbalancing:SetSubnets",
    "elasticloadbalancing:DeleteLoadBalancer",
    "elasticloadbalancing:ModifyTargetGroup",
    "elasticloadbalancing:ModifyTargetGroupAttributes",
    "elasticloadbalancing:DeleteTargetGroup",
    "elasticloadbalancing:ModifyListenerAttributes",
    "elasticloadbalancing:ModifyCapacityReservation",
    "elasticloadbalancing:RegisterTargets",
    "elasticloadbalancing:DeregisterTargets",
    "elasticloadbalancing:SetWebAcl",
    "elasticloadbalancing:ModifyListener",
    "elasticloadbalancing:AddListenerCertificates",
    "elasticloadbalancing:RemoveListenerCertificates",
    "elasticloadbalancing:ModifyRule",
]
AWS_LOAD_BALANCER_CONTROLLER_POLICY = json.dumps(
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": AWS_LOAD_BALANCER_CONTROLLER_ACTIONS,
                "Resource": "*",
            }
        ],
    },
    indent=12,
)
AWS_LOAD_BALANCER_CONTROLLER_TEMPLATE = (
    "Resources:\n"
    "  LoadBalancerControllerPolicy:\n"
    "    Type: AWS::IAM::ManagedPolicy\n"
    "    Properties:\n"
    "      PolicyDocument: |\n"
    f"{indent(AWS_LOAD_BALANCER_CONTROLLER_POLICY, '        ')}\n"
)
INVALID_DESCRIPTION = "      Description: []\n"


@pytest.fixture
def managed_policy_validator(validator):
    return validator.evolve(
        context=validator.context.evolve(
            path=validator.context.path.evolve(
                cfn_path=MANAGED_POLICY_DOCUMENT_PATH,
            )
        )
    )


def _errors(managed_policy_validator, policy_document):
    return list(
        StringLength().maxLength(
            managed_policy_validator,
            MAX_MANAGED_POLICY_SIZE,
            policy_document,
            POLICY_DOCUMENT_SCHEMA,
        )
    )


def _object_document_with_size(size):
    # Compact JSON for {"x":"..."} contributes eight structural characters.
    return {"x": "a" * (size - 8)}


def _with_invalid_description(template):
    return template.replace(
        "      PolicyDocument:",
        f"{INVALID_DESCRIPTION}      PolicyDocument:",
        1,
    )


def _rule_signatures(matches, rule_id):
    return [
        (match.rule.id, match.message, tuple(match.path))
        for match in matches
        if match.rule.id == rule_id
    ]


@pytest.fixture(scope="module")
def aws_load_balancer_controller_matches():
    return lint(AWS_LOAD_BALANCER_CONTROLLER_TEMPLATE)


def test_mpol_001_managed_policy_spaces_tabs_cr_lf_are_excluded_from_size(
    managed_policy_validator,
):
    """GUID: MPOL-001 - Ignore specified whitespace when measuring document size."""
    document = _object_document_with_size(MAX_MANAGED_POLICY_SIZE)
    document["x"] += " \t\r\n" * 100

    assert _errors(managed_policy_validator, document) == []
    assert _errors(
        managed_policy_validator,
        "a" * MAX_MANAGED_POLICY_SIZE + " \t\r\n" * 100,
    ) == []


@pytest.mark.parametrize("size", [MAX_MANAGED_POLICY_SIZE, MAX_MANAGED_POLICY_SIZE + 1])
def test_mpol_001_managed_policies_differing_only_by_whitespace_match_outcome(
    managed_policy_validator, size
):
    """GUID: MPOL-001 - Whitespace-only differences preserve the size outcome."""
    compact = _object_document_with_size(size)
    whitespace_variant = _object_document_with_size(size)
    whitespace_variant["x"] = (
        " \t" + whitespace_variant["x"] + "\r\n" * 200
    )

    assert bool(_errors(managed_policy_validator, compact)) == bool(
        _errors(managed_policy_validator, whitespace_variant)
    )


def test_mpol_002_managed_policy_below_6144_non_whitespace_has_no_e3033(
    managed_policy_validator,
):
    """GUID: MPOL-002 - A document below the inclusive limit passes E3033."""
    assert _errors(
        managed_policy_validator,
        _object_document_with_size(MAX_MANAGED_POLICY_SIZE - 1),
    ) == []


def test_mpol_002_managed_policy_at_6144_non_whitespace_has_no_e3033(
    managed_policy_validator,
):
    """GUID: MPOL-002 - A document at the inclusive limit passes E3033."""
    assert _errors(
        managed_policy_validator,
        _object_document_with_size(MAX_MANAGED_POLICY_SIZE),
    ) == []


def test_mpol_003_managed_policy_above_6144_non_whitespace_produces_e3033(
    managed_policy_validator,
):
    """GUID: MPOL-003 - A document above the limit produces E3033."""
    errors = _errors(
        managed_policy_validator,
        _object_document_with_size(MAX_MANAGED_POLICY_SIZE + 1),
    )

    assert len(errors) == 1
    assert errors[0].message == "Item is too long"


def test_mpol_004_aws_load_balancer_controller_block_scalar_has_no_size_e3033(
    aws_load_balancer_controller_matches,
):
    """GUID: MPOL-004 - The supplied block-scalar policy has no size E3033."""
    assert len(AWS_LOAD_BALANCER_CONTROLLER_POLICY) > MAX_MANAGED_POLICY_SIZE
    assert (
        len(AWS_LOAD_BALANCER_CONTROLLER_POLICY.translate(MANAGED_POLICY_WHITESPACE))
        <= MAX_MANAGED_POLICY_SIZE
    )
    assert [
        match
        for match in aws_load_balancer_controller_matches
        if match.rule.id == "E3033"
    ] == []


def test_mpol_004_aws_load_balancer_controller_block_scalar_has_no_associated_e3001(
    aws_load_balancer_controller_matches,
):
    """GUID: MPOL-004 - The supplied block-scalar policy has no associated E3001."""
    assert [
        match
        for match in aws_load_balancer_controller_matches
        if match.rule.id == "E3001"
    ] == []


def test_mpol_005_unrelated_result_unchanged_after_policy_size_correction():
    """GUID: MPOL-005 - Preserve an unrelated result after size correction."""
    compact_policy = json.dumps(json.loads(AWS_LOAD_BALANCER_CONTROLLER_POLICY))
    compact_template = AWS_LOAD_BALANCER_CONTROLLER_TEMPLATE.replace(
        indent(AWS_LOAD_BALANCER_CONTROLLER_POLICY, "        "),
        indent(compact_policy, "        "),
    )
    compact_matches = lint(_with_invalid_description(compact_template))
    corrected_matches = lint(
        _with_invalid_description(AWS_LOAD_BALANCER_CONTROLLER_TEMPLATE)
    )

    assert _rule_signatures(corrected_matches, "E3012") == _rule_signatures(
        compact_matches, "E3012"
    )


def test_mpol_005_size_and_separate_invalid_condition_preserves_unrelated_result():
    """GUID: MPOL-005 - Size correction does not suppress a separate result."""
    matches = lint(_with_invalid_description(AWS_LOAD_BALANCER_CONTROLLER_TEMPLATE))

    assert len(AWS_LOAD_BALANCER_CONTROLLER_POLICY) > MAX_MANAGED_POLICY_SIZE
    assert _rule_signatures(matches, "E3033") == []
    assert _rule_signatures(matches, "E3012") == [
        (
            "E3012",
            "[] is not of type 'string'",
            ("Resources", "LoadBalancerControllerPolicy", "Properties", "Description"),
        )
    ]
