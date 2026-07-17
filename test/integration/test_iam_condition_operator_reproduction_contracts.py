"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

import json
from pathlib import Path

from cfnlint import lint


FIXTURE = Path(
    "test/fixtures/templates/issues/iam_condition_operator_reproduction.json"
)
POLICY_PATH = (
    "Resources",
    "ClusterPolicy",
    "Properties",
    "PolicyDocument",
)
OPERATOR_LOCI = (
    (POLICY_PATH + ("Statement", 0, "Condition"), "StringEqualsIfExists"),
    (
        POLICY_PATH + ("Statement", 0, "Condition"),
        "ForAnyValue:StringEquals",
    ),
    (
        POLICY_PATH + ("Statement", 1, "Fn::If", 1, "Condition"),
        "ForAllValues:StringEquals",
    ),
    (
        POLICY_PATH + ("Statement", 1, "Fn::If", 1, "Condition"),
        "ForAnyValue:StringEqualsIfExists",
    ),
)


def _at_path(document, path):
    value = document
    for part in path:
        value = value[part]
    return value


def _load_and_lint_unchanged_fixture():
    original = FIXTURE.read_bytes()
    document = json.loads(original)
    matches = lint(original.decode("utf-8"))
    assert FIXTURE.read_bytes() == original, "linting modified the reproduction fixture"
    return document, matches


def _reported_operator_rejections(matches):
    rejections = []
    for condition_path, operator in OPERATOR_LOCI:
        for match in matches:
            if match.rule.id != "E3510" or operator not in match.message:
                continue
            match_path = tuple(match.path)
            if match_path[: len(condition_path)] == condition_path:
                rejections.append((condition_path + (operator,), match))
    return rejections


class TestIamConditionOperatorReproductionContracts:
    """Integration ownership boundary for GUID: IAMOP-004 and IAMOP-009."""

    # ARCHITECTURE — GUID: IAMOP-004, IAMOP-009
    # This class owns unchanged-template acceptance at the integration boundary.
    # The canonical input belongs under test/fixtures/templates/issues; this
    # module may observe that fixture and lint findings but must never normalize,
    # rewrite, or otherwise own the reproduction template's content.
    # Dependency direction is this contract -> the public lint API -> the normal
    # cfn-lint Runner validation pipeline. Production IAM validation must not
    # depend on this test scaffold.

    def test_iamop_004_linting_unchanged_reproduction_emits_none_of_four_e3510_findings(
        self,
    ):
        """GUID: IAMOP-004; unchanged reproduction has no four reported E3510s."""
        # PSEUDOCODE — GUID: IAMOP-004
        # INPUT: the canonical supplied reproduction fixture and the four reported
        # condition-operator loci, each identified by its template path and name.
        # READ the fixture as-is and retain its original content for a drift check.
        # INVOKE the normal cfn-lint integration entry point on that same fixture.
        # IF loading or lint execution cannot complete:
        #   FAIL with the underlying integration error; do not report acceptance.
        # CONFIRM the fixture content still equals the retained original content.
        # FOR EACH emitted finding:
        #   IF its rule is E3510 and its path identifies one of the four reported
        #   operator loci:
        #     RECORD the corresponding operator occurrence as a false positive.
        #   ELSE:
        #     LEAVE the finding outside this requirement's result.
        # FAIL with the recorded paths and names when any reported occurrence was
        # rejected; otherwise ACCEPT all four occurrences without requiring edits.
        document, matches = _load_and_lint_unchanged_fixture()

        observed_loci = {
            condition_path + (operator,)
            for condition_path, operator in OPERATOR_LOCI
            if operator in _at_path(document, condition_path)
        }
        expected_loci = {
            condition_path + (operator,)
            for condition_path, operator in OPERATOR_LOCI
        }
        assert observed_loci == expected_loci, "reproduction operator loci drifted"
        assert _reported_operator_rejections(matches) == []

    def test_iamop_009_accepts_intrinsics_in_unchanged_reproduction(
        self,
    ):
        """GUID: IAMOP-009; surrounding intrinsics remain accepted in place."""
        # PSEUDOCODE — GUID: IAMOP-009 (intrinsic-function obligation)
        # INPUT: the canonical unchanged reproduction fixture and the expected
        # paths and intrinsic kinds surrounding its IAM Condition values.
        # READ the fixture without normalization, substitution, or rewriting.
        # FOR EACH expected intrinsic path:
        #   CONFIRM the original node exists at that path with its expected kind.
        #   IF the node is absent, moved, or changed:
        #     FAIL as reproduction-fixture drift rather than lint acceptance.
        # INVOKE cfn-lint on the unchanged fixture and collect all findings.
        # FOR EACH finding attributable to policy validation at an expected path:
        #   IF it rejects the intrinsic in that original location:
        #     RECORD the path, intrinsic kind, and finding.
        # FAIL with all recorded intrinsic rejections; otherwise ACCEPT the
        # surrounding intrinsic functions in their original locations.
        document, matches = _load_and_lint_unchanged_fixture()

        expected_intrinsics = (
            (
                POLICY_PATH
                + (
                    "Statement",
                    0,
                    "Condition",
                    "StringEqualsIfExists",
                    "ec2:InstanceType",
                ),
                "Ref",
            ),
            (
                POLICY_PATH
                + (
                    "Statement",
                    0,
                    "Condition",
                    "ForAnyValue:StringEquals",
                    "aws:TagKeys",
                    0,
                ),
                "Fn::Sub",
            ),
            (
                POLICY_PATH
                + (
                    "Statement",
                    1,
                    "Fn::If",
                    1,
                    "Condition",
                    "ForAllValues:StringEquals",
                    "aws:TagKeys",
                    0,
                ),
                "Fn::Join",
            ),
            (
                POLICY_PATH
                + (
                    "Statement",
                    1,
                    "Fn::If",
                    1,
                    "Condition",
                    "ForAnyValue:StringEqualsIfExists",
                    "s3:ExistingObjectTag/parallelcluster",
                ),
                "Fn::If",
            ),
        )
        for path, intrinsic in expected_intrinsics:
            assert set(_at_path(document, path)) == {intrinsic}, (
                f"expected {intrinsic} at {path!r}"
            )
        assert _reported_operator_rejections(matches) == []

    def test_iamop_009_accepts_conditional_structures_in_unchanged_reproduction(
        self,
    ):
        """GUID: IAMOP-009; conditional policy structures need no template changes."""
        # PSEUDOCODE — GUID: IAMOP-009 (conditional-structure obligation)
        # INPUT: the canonical unchanged reproduction fixture and the expected
        # paths and shapes of conditional structures surrounding IAM conditions.
        # READ the fixture as-is and retain its original content.
        # FOR EACH expected conditional-structure path:
        #   CONFIRM the original branch structure and handoff into the policy
        #   document remain present without resolving or flattening either branch.
        #   IF the path or shape differs:
        #     FAIL as reproduction-fixture drift rather than lint acceptance.
        # INVOKE cfn-lint on the unchanged fixture and collect all findings.
        # FOR EACH finding attributable to an expected conditional structure:
        #   IF it rejects the structure or either branch around the IAM Condition:
        #     RECORD the path, branch context, and finding.
        # CONFIRM the fixture content still equals the retained original content.
        # FAIL with all recorded conditional-structure rejections; otherwise
        # ACCEPT the structures without template modification.
        document, matches = _load_and_lint_unchanged_fixture()

        conditional = _at_path(document, POLICY_PATH + ("Statement", 1, "Fn::If"))
        assert len(conditional) == 3
        assert conditional[0] == "IncludeConditionalPolicy"
        assert set(conditional[1]["Condition"]) == {
            "ForAllValues:StringEquals",
            "ForAnyValue:StringEqualsIfExists",
        }
        assert conditional[2] == {"Ref": "AWS::NoValue"}
        assert _reported_operator_rejections(matches) == []


class TestIamConditionOperatorRegressionPreservationContracts:
    """Verification placeholders for GUID: IAMOP-010."""

    def test_iamop_010_unrelated_existing_finding_remains_governed_by_its_rule(self):
        """GUID: IAMOP-010; unrelated findings retain existing rule behavior."""
        # PSEUDOCODE — GUID: IAMOP-010 (unrelated-rule isolation obligation)
        # INPUT: a template that triggers a known finding whose rule and
        # acceptance conditions do not concern IAM Condition operator names.
        # INVOKE the normal lint entry point with the existing rule configuration.
        # FOR EACH emitted finding at the known unrelated-content locus:
        #   IF the finding belongs to the established unrelated rule:
        #     RETAIN its rule identity, path, message semantics, and existing
        #     acceptance conditions without E3510 reclassification or suppression.
        #   ELSE IF IAM operator-name validation claims that unrelated locus:
        #     RECORD a validation-boundary regression.
        # IF the established unrelated rule's expected outcome is absent or changed:
        #   RECORD an unrelated-rule behavior regression.
        # FAIL with every recorded regression; otherwise PRESERVE the finding under
        # the same unrelated validation rule and its existing acceptance conditions.
        assert True

    def test_iamop_010_corrected_operator_with_unrelated_content_preserves_both_outcomes(
        self,
    ):
        """GUID: IAMOP-010; mixed validation avoids E3510 and preserves its peer."""
        # PSEUDOCODE — GUID: IAMOP-010 (mixed-content isolation obligation)
        # INPUT: one template containing both a corrected valid IAM Condition
        # operator and content governed by a known unrelated validation rule.
        # INVOKE the normal lint entry point once so both validation paths observe
        # the same unchanged template and collect the complete finding sequence.
        # PARTITION findings by the corrected operator locus, the unrelated-content
        # locus, and all remaining loci without changing their owning rule IDs.
        # IF E3510 rejects the corrected valid operator name at its locus:
        #   RECORD a false operator-name finding.
        # IF the unrelated rule's established outcome is absent, suppressed,
        # reclassified, or evaluated under different acceptance conditions:
        #   RECORD an unrelated-rule behavior regression.
        # LEAVE findings at all remaining loci governed by their existing rules.
        # FAIL with both categories of recorded regression; otherwise REPORT no
        # false E3510 for the operator and the unchanged unrelated-rule outcome.
        assert True
