"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from typing import Any

from cfnlint.jsonschema import ValidationError, ValidationResult, Validator
from cfnlint.rules.resources.iam.Policy import Policy


class IdentityPolicy(Policy):
    """Check IAM identity Policies"""

    _ROLE_INLINE_POLICY_KEYWORD = (
        "Resources/AWS::IAM::Role/Properties/Policies/*/PolicyDocument"
    )

    # IAMSID-001, IAMSID-002 architecture contract:
    # - This rule owns the check because its keyword registry selects each identity
    #   PolicyDocument and its validator already owns IAM-policy diagnostics.
    # - The implementation seam is IdentityPolicy.validate, composed around
    #   Policy.validate so the base class remains the sole owner of schema errors.
    # - The policy_type argument carries the matched cfnLint keyword. Gate the new
    #   check on the AWS::IAM::Role inline-policy keyword below; the other registered
    #   identity-policy locations remain outside these requirements.
    # - Emit a ValidationError with a path relative to the selected PolicyDocument.
    #   The existing cfnLint dispatch composes that relative statement path with the
    #   template path, preserving IAMSID-002 without coupling this rule to templates.

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
                self._ROLE_INLINE_POLICY_KEYWORD,
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

    def validate(
        self,
        validator: Validator,
        policy_type: Any,
        policy: Any,
        schema: dict[str, Any],
    ) -> ValidationResult:
        """Validate the policy schema and duplicate Role inline-policy Sids."""
        yield from super().validate(validator, policy_type, policy, schema)

        if policy_type != self._ROLE_INLINE_POLICY_KEYWORD:
            return

        yield from self._iter_duplicate_concrete_sid_errors(policy)

    def _iter_duplicate_concrete_sid_errors(self, policy: Any) -> ValidationResult:
        """IAMSID-001, IAMSID-002: report repeated concrete statement Sids."""
        if not isinstance(policy, dict):
            return

        statements = policy.get("Statement")
        if not isinstance(statements, list):
            return

        first_statement_index_by_sid: dict[str, int] = {}
        reported_sids: set[str] = set()

        for statement_index, statement in enumerate(statements):
            if not isinstance(statement, dict):
                continue

            sid = statement.get("Sid")
            if not isinstance(sid, str):
                continue

            if sid not in first_statement_index_by_sid:
                first_statement_index_by_sid[sid] = statement_index
                continue

            if sid in reported_sids:
                continue

            yield ValidationError(
                f"Statement Sid {sid!r} is duplicated",
                path=("Statement", statement_index, "Sid"),
                rule=self,
            )
            reported_sids.add(sid)
