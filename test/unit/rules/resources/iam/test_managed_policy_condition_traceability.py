"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from collections import deque

from cfnlint.context import Context, Path
from cfnlint.jsonschema import CfnTemplateValidator
from cfnlint.rules.resources.iam.IdentityPolicy import IdentityPolicy


# ARCHITECTURE (IAMCOND-006, IAMCOND-008):
# This module remains the regression owner because it already provides the
# managed-policy PolicyDocument context and the condition-finding observation
# boundary.  `_validate` is the test-only execution adapter and explicit
# IdentityPolicy check-selection seam; repeated and malformed-versus-valid
# scenarios must enter through that same adapter with unchanged surrounding
# policy data.  Production code has no dependency on this test seam.
#
# `_condition_operator_errors` is the shared diagnostic-selection boundary for
# both requirements.  IAMCOND-006 owns comparison of emitted rule identity,
# message, and path at the test locus, without adding sorting or determinism
# machinery to IdentityPolicy.  IAMCOND-008 owns two tests in the existing class
# that share this adapter and filter while varying only the Condition structure.
# Pytest's existing discovery of this module is the suite-integration seam, so no
# new fixture module, runner configuration, or public production API is needed.


def _validate(
    condition,
    resource_type="AWS::IAM::ManagedPolicy",
    effect="Allow",
):
    rule = IdentityPolicy()
    validator = CfnTemplateValidator().evolve(
        context=Context(
            path=Path(
                cfn_path=deque(
                    ["Resources", resource_type, "Properties", "PolicyDocument"]
                )
            )
        )
    )
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": effect,
                "Action": "servicecatalog:ListPortfolios",
                "Resource": "*",
                "Condition": condition,
            }
        ],
    }
    return list(rule.validate(validator, None, policy, {}))


def _condition_operator_errors(errors):
    return [
        error
        for error in errors
        if "condition operator" in error.message.lower()
    ]


class TestManagedPolicyConditionTraceability:
    """Contracts for malformed managed-policy conditions."""

    def test_iamcond_001_info_checks_direct_key_report_missing_operator(self):
        """IAMCOND-001: reproduced malformed policy reports a missing operator."""
        errors = _condition_operator_errors(
            _validate({"servicecatalog:accountLevel": "account"})
        )

        assert len(errors) == 1
        assert "missing or invalid" in errors[0].message.lower()

    def test_iamcond_002_equivalent_direct_key_reports_invalid_operator(self):
        """IAMCOND-002: any equivalent direct condition key reports an error."""
        errors = _condition_operator_errors(
            _validate({"aws:PrincipalArn": "arn:aws:iam::123456789012:root"})
        )

        assert len(errors) == 1

    def test_iamcond_004_namespace_child_is_key_not_operator(self):
        """IAMCOND-004: a namespace-separated child is a key, not an operator."""
        errors = _condition_operator_errors(
            _validate(
                {
                    "ForAllValues:StringEquals": {
                        "aws:TagKeys": ["environment", "cost-center"]
                    },
                    "servicecatalog:accountLevel": "account",
                }
            )
        )

        assert len(errors) == 1
        assert errors[0].path[-1] == "servicecatalog:accountLevel"

    def test_iamcond_005_finding_points_to_condition_or_direct_child(self):
        """IAMCOND-005: the finding locates Condition or its direct child."""
        errors = _condition_operator_errors(
            _validate({"servicecatalog:accountLevel": "account"})
        )

        assert list(errors[0].path) == [
            "Statement",
            0,
            "Condition",
            "servicecatalog:accountLevel",
        ]

    def test_iamcond_003_valid_managed_policy_operator_condition_produces_no_missing_or_invalid_operator_finding(
        self,
    ):
        """IAMCOND-003: a valid operator condition produces no operator finding."""
        errors = _condition_operator_errors(
            _validate(
                {
                    "StringEquals": {
                        "servicecatalog:accountLevel": "account",
                    }
                }
            )
        )

        assert errors == []

    def test_iamcond_007_unrelated_lint_findings_remain_unchanged(self):
        """IAMCOND-007: findings outside IAM Condition structure remain unchanged."""
        condition = {
            "StringEquals": {
                "servicecatalog:accountLevel": "account",
            }
        }
        managed_policy_errors = _validate(condition, effect="NotAllow")
        inline_policy_errors = _validate(
            condition,
            resource_type="AWS::IAM::Policy",
            effect="NotAllow",
        )

        def error_details(errors):
            return [(error.message, list(error.path)) for error in errors]

        assert error_details(managed_policy_errors) == error_details(
            inline_policy_errors
        )
        assert error_details(managed_policy_errors) == [
            (
                "'NotAllow' is not one of ['Allow', 'Deny']",
                ["Statement", 0, "Effect"],
            )
        ]

    def test_iamcond_006_identical_template_and_check_selection_repeatedly_produce_identical_condition_findings(
        self,
    ):
        """IAMCOND-006: identical lint inputs produce deterministic findings."""
        condition = {"servicecatalog:accountLevel": "account"}

        def finding_details():
            return [
                (error.rule.id, error.message, list(error.path))
                for error in _condition_operator_errors(_validate(condition))
            ]

        baseline = finding_details()

        assert len(baseline) == 1
        for _ in range(5):
            assert finding_details() == baseline

    def test_iamcond_008_malformed_direct_key_condition_produces_missing_or_invalid_operator_finding(
        self,
    ):
        """IAMCOND-008: the reproduced malformed condition produces a finding."""
        errors = _condition_operator_errors(
            _validate({"servicecatalog:accountLevel": "account"})
        )

        assert len(errors) == 1
        assert "missing or invalid" in errors[0].message.lower()
        assert errors[0].rule.id == "E3510"
        assert list(errors[0].path) == [
            "Statement",
            0,
            "Condition",
            "servicecatalog:accountLevel",
        ]

    def test_iamcond_008_valid_operator_key_value_condition_produces_no_missing_or_invalid_operator_finding(
        self,
    ):
        """IAMCOND-008: a valid operator-key-value condition avoids the finding."""
        errors = _condition_operator_errors(
            _validate(
                {
                    "StringEquals": {
                        "servicecatalog:accountLevel": "account",
                    }
                }
            )
        )

        assert errors == []
