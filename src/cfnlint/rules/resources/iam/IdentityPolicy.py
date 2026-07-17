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
        # PSEUDOCODE — GUID: IAMOP-005, IAMOP-006
        # INPUT: every Condition operator name in an identity policy reached
        # through one of the registered policy-document keywords below.
        # OBTAIN the closed set of AWS-defined operator names in their exact,
        # case-sensitive spellings; do not normalize or case-fold input names.
        # FOR EACH supplied operator name, independently:
        #   IF the name exactly matches one member of the closed set:
        #     ACCEPT it for subsequent Condition-value validation and emit no
        #     operator-name finding, even when another name is invalid.
        #   ELSE IF it differs from a closed-set member only by letter case:
        #     REJECT it with the applicable identity-policy validation finding
        #     and preserve the supplied spelling in the failure locus.
        #   ELSE:
        #     REJECT the genuinely invalid name with the applicable validation
        #     finding and preserve its operator locus for diagnostic handoff.
        # OUTPUT: one independent name-validation result per supplied operator;
        # valid names proceed, while all invalid or incorrectly cased names fail.
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
