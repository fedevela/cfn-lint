"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from cfnlint.rules.resources.iam.Policy import Policy


class IdentityPolicy(Policy):
    """Check IAM identity Policies"""

    # ARCHITECTURE (IAMCOND-001, IAMCOND-002, IAMCOND-004, IAMCOND-005):
    # This rule owns the managed-policy condition check because it already owns
    # the AWS::IAM::ManagedPolicy PolicyDocument integration path.  The Policy
    # base remains the shared schema-validation boundary; policy.json remains a
    # shared contract for every identity-policy resource and must not acquire
    # this managed-policy-only behavior.
    #
    # The implementation seam is a private validator owned by IdentityPolicy.
    # It receives the policy instance and Validator context, uses the context's
    # CloudFormation path to enforce the managed-policy boundary, and returns
    # ValidationResult entries with paths relative to PolicyDocument.  Condition
    # operator recognition stays behind that seam so namespace-bearing condition
    # keys cannot become dependencies or extensions of the shared policy schema.
    # IdentityPolicy.validate is the sole integration point: shared Policy
    # validation remains upstream, and the private managed-policy check contributes
    # findings through the same ValidationResult stream without a public API.

    id = "E3510"
    shortdesc = "Validate identity based IAM polices"
    description = (
        "IAM identity polices are embedded JSON in CloudFormation. "
        "This rule validates those embedded policies."
    )
    source_url = "https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_identity-vs-resource.html"
    tags = ["resources", "iam"]

    def __init__(self):
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

        # IAMCOND-001, IAMCOND-002, IAMCOND-004, IAMCOND-005 — logic obligation:
        # detect a condition key placed where a condition operator is required in
        # an AWS::IAM::ManagedPolicy, and locate the resulting finding precisely.
        #
        # PSEUDOCODE validate_managed_policy_condition(policy_document, policy_path):
        #   IF policy_path is not an AWS::IAM::ManagedPolicy PolicyDocument:
        #     RETURN without applying this managed-policy-specific check
        #   FOR EACH statement in the policy document, preserving its source path:
        #     IF statement.Condition is absent:
        #       CONTINUE
        #     IF statement.Condition cannot be traversed as an object:
        #       HAND OFF to the existing policy-schema type-validation path
        #       CONTINUE
        #     FOR EACH direct_child_name in statement.Condition:
        #       IF direct_child_name matches the recognized IAM condition-operator
        #       grammar or catalog:
        #         HAND OFF its value for normal operator/value validation
        #         CONTINUE
        #       CLASSIFY direct_child_name as a condition key, not an operator;
        #       namespace separation (for example, "servicecatalog:accountLevel")
        #       does not make the name an operator
        #       EMIT one missing-or-invalid-condition-operator finding
        #       SET finding.path to statement.Condition/direct_child_name;
        #       statement.Condition itself is the permitted fallback locus
        #   RETURN all findings through the active lint pass (including when
        #   informational checks are enabled)
