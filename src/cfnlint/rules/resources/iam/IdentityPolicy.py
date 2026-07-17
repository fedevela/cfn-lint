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

    # IAMSID-001, IAMSID-002 logic obligation:
    # Report a duplicate concrete Sid within one qualifying identity-policy
    # document, and anchor the required diagnostic to a statement that repeats it.
    #
    # PSEUDOCODE _iter_duplicate_concrete_sid_errors(policy_document):
    #   INPUT: the single PolicyDocument selected by this rule's configured path
    #   IF policy_document is not a mapping OR Statement is not a sequence:
    #       RETURN; existing schema validation owns the malformed-shape error path
    #   SET first_statement_index_by_sid to an empty mapping
    #   SET required_diagnostic_emitted_by_sid to an empty set
    #   FOR EACH statement, statement_index IN PolicyDocument.Statement IN order:
    #       IF statement is not a mapping:
    #           CONTINUE; existing schema validation owns this statement error path
    #       SET sid to statement.Sid
    #       IF sid is absent OR sid is not a concrete string:
    #           CONTINUE; unresolved or non-concrete Sids cannot prove duplication
    #       IF sid is not in first_statement_index_by_sid:
    #           RECORD statement_index as the first occurrence of sid
    #           CONTINUE
    #       IF sid is not in required_diagnostic_emitted_by_sid:
    #           YIELD a duplicate-Sid lint error whose relative path is
    #               ["Statement", statement_index, "Sid"]
    #           RECORD that the required diagnostic for sid has been emitted
    #       CONTINUE scanning so three-or-more equal Sids remain detected as a group;
    #           any additional diagnostics are outside IAMSID-001 and IAMSID-002
    #   OUTPUT: zero or more requirement-mandated errors at relevant statements
