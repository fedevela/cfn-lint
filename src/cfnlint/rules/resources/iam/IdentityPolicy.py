"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from cfnlint.rules.resources.iam.Policy import Policy


class IdentityPolicy(Policy):
    """Check IAM identity Policies"""

    id = "E3510"
    shortdesc = "Validate identity based IAM polices"
    description = (
        "IAM identity polices are embedded JSON in CloudFormation. "
        "This rule validates those embedded policies."
    )
    source_url = "https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_identity-vs-resource.html"
    tags = ["resources", "iam"]

    def __init__(self):
        # PSEUDOCODE — GUID: IAMOP-001, IAMOP-002, IAMOP-003, IAMOP-007
        # INPUT: an identity-policy Condition operator reached through the
        # AWS::IAM::ManagedPolicy or AWS::IAM::Policy keyword below.
        # OBTAIN the canonical, exactly spelled documented IAM operator names,
        # including AWS-defined IfExists, ForAnyValue:, and ForAllValues: forms.
        # FOR EACH operator name in the Condition mapping:
        #   IF it exactly matches a canonical documented name:
        #     ACCEPT the name and hand its value to normal Condition validation.
        #     This includes StringEqualsIfExists (IAMOP-001),
        #     ForAnyValue:StringEquals (IAMOP-002), and
        #     ForAllValues:StringEquals (IAMOP-003).
        #   ELSE:
        #     PRESERVE the operator-name E3510 finding; do not normalize an
        #     approximate spelling or infer validity from modifier-like syntax.
        # OUTPUT: documented exact names continue without an operator-name
        # finding; malformed, undocumented, or arbitrary names remain errors.
        super().__init__(
            [
                "Resources/AWS::IAM::Group/Properties/Policies/*/PolicyDocument",
                "Resources/AWS::IAM::ManagedPolicy/Properties/PolicyDocument",
                "Resources/AWS::IAM::Policy/Properties/PolicyDocument",
                "Resources/AWS::IAM::Role/Properties/Policies/*/PolicyDocument",
                "Resources/AWS::IAM::User/Properties/Policies/*/PolicyDocument",
                "Resources/AWS::SSO::PermissionSet/Properties/InlinePolicy",
            ],
            "identity",
            "policy_identity.json",
        )
