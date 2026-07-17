"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from __future__ import annotations

import json
from collections import deque
from typing import Any

from cfnlint.helpers import FUNCTIONS
from cfnlint.jsonschema import ValidationError, ValidationResult, Validator
from cfnlint.rules.resources.iam.Policy import Policy


class IdentityPolicy(Policy):
    """Check IAM identity Policies"""

    _CONDITION_OPERATORS = frozenset(
        {
            "ArnEquals",
            "ArnLike",
            "ArnNotEquals",
            "ArnNotLike",
            "BinaryEquals",
            "Bool",
            "DateEquals",
            "DateGreaterThan",
            "DateGreaterThanEquals",
            "DateLessThan",
            "DateLessThanEquals",
            "DateNotEquals",
            "IpAddress",
            "NotIpAddress",
            "Null",
            "NumericEquals",
            "NumericGreaterThan",
            "NumericGreaterThanEquals",
            "NumericLessThan",
            "NumericLessThanEquals",
            "NumericNotEquals",
            "StringEquals",
            "StringEqualsIgnoreCase",
            "StringLike",
            "StringNotEquals",
            "StringNotEqualsIgnoreCase",
            "StringNotLike",
        }
    )
    _SET_QUALIFIERS = frozenset({"ForAllValues", "ForAnyValue"})
    _MANAGED_POLICY_PATH = (
        "Resources/AWS::IAM::ManagedPolicy/Properties/PolicyDocument"
    )

    # ARCHITECTURE (IAMCOND-001, IAMCOND-002, IAMCOND-003, IAMCOND-004,
    # IAMCOND-005, IAMCOND-007):
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
    # The private operator classifier is the acceptance contract for IAMCOND-003;
    # valid operator branches remain inside this rule and outside its diagnostic
    # output boundary.
    # IdentityPolicy.validate is the sole integration point: shared Policy
    # validation remains upstream, and the private managed-policy check contributes
    # findings through the same ValidationResult stream without a public API.
    # That one-way dependency preserves IAMCOND-007: the supplemental seam may add
    # condition-structure findings but does not own or transform upstream findings.

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

    @classmethod
    def _is_condition_operator(cls, name: Any) -> bool:
        if not isinstance(name, str):
            return False

        qualifier, separator, operator = name.partition(":")
        if separator:
            if qualifier not in cls._SET_QUALIFIERS or ":" in operator:
                return False
        else:
            operator = qualifier

        if operator.endswith("IfExists"):
            operator = operator[: -len("IfExists")]
            if operator == "Null":
                return False

        return operator in cls._CONDITION_OPERATORS

    def _validate_managed_policy_conditions(
        self, policy: Any
    ) -> ValidationResult:
        if not isinstance(policy, dict):
            return

        statements = policy.get("Statement", [])
        if isinstance(statements, dict):
            statements = [statements]
        if not isinstance(statements, list):
            return

        for statement_index, statement in enumerate(statements):
            if not isinstance(statement, dict):
                continue
            condition = statement.get("Condition")
            if not isinstance(condition, dict):
                continue

            statement_path: list[str | int] = ["Statement"]
            if isinstance(policy.get("Statement"), list):
                statement_path.append(statement_index)
            statement_path.append("Condition")

            for child_name in condition:
                # PSEUDOCODE (IAMCOND-003) — valid-condition acceptance:
                # INPUT the direct child between Condition and its condition key.
                # IF the child is an intrinsic-function handoff, SKIP operator
                # classification and PRODUCE no missing-or-invalid finding here.
                # ELSE IF the child is a recognized condition operator (including
                # its permitted qualifier/suffix forms), MARK this branch valid,
                # CONTINUE with the next child, and PRODUCE no operator finding.
                # ELSE HAND OFF to the malformed-condition diagnostic path below.
                if child_name in FUNCTIONS or self._is_condition_operator(child_name):
                    continue
                yield ValidationError(
                    (
                        f"Missing or invalid condition operator for {child_name!r}; "
                        "condition keys must be nested beneath an operator"
                    ),
                    path=deque([*statement_path, child_name]),
                    rule=self,
                )

    def validate(
        self,
        validator: Validator,
        policy_type: Any,
        policy: Any,
        schema: dict[str, Any],
    ) -> ValidationResult:
        # PSEUDOCODE (IAMCOND-007) — unrelated-behavior preservation:
        # INPUT the shared identity-policy validation stream and EMIT every
        # pre-existing result unchanged; do not filter, replace, or reorder it.
        # IF the context is not the managed-policy PolicyDocument locus, RETURN
        # without invoking condition-structure validation.
        # IF a managed policy is string encoded, ATTEMPT decoding; on decoding
        # failure, RETURN after the shared results already emitted.
        # OTHERWISE HAND OFF the decoded/object policy to the supplemental
        # condition validator and EMIT only the findings that validator produces.
        # NEVER alter findings outside the IAM Condition structure.
        yield from super().validate(validator, policy_type, policy, schema)

        if validator.context.path.cfn_path_string != self._MANAGED_POLICY_PATH:
            return

        if validator.is_type(policy, "string"):
            try:
                policy = json.loads(policy)
            except json.JSONDecodeError:
                return

        # IAMCOND-001, IAMCOND-002, IAMCOND-004, IAMCOND-005
        yield from self._validate_managed_policy_conditions(policy)
