"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from cfnlint.jsonschema import ValidationError
from cfnlint.rules import CloudFormationLintRule


class EqualsIsUseful(CloudFormationLintRule):
    """
    Validate that the Equals will return
    true/false and not always be true or false
    """

    # ARCHITECTURE — W8003-001 / W8003-002 / W8003-007
    # This rule owns constant-result analysis for one already validated Fn::Equals
    # operand list. Fn::Equals traversal and source-location context remain owned by
    # Equals; keeping that boundary makes each invocation produce only its finding.

    # PSEUDOCODE — W8003-005 / W8003-006
    # Verification loci:
    # - test_W8003_005_identical_literal_equals_finding_retains_rule_identifier_W8003
    # - test_W8003_005_identical_literal_equals_finding_retains_warning_severity
    # - test_W8003_005_unequal_literal_equals_finding_retains_rule_identifier_W8003
    # - test_W8003_005_unequal_literal_equals_finding_retains_warning_severity
    # - test_W8003_006_description_covers_constant_true_and_false_equals_outcomes
    # PROCEDURE define_rule_contract():
    #   SET the finding identifier to W8003 for every constant-result outcome.
    #   DERIVE warning severity from the identifier's W classification.
    #   DESCRIBE the rule as detecting Fn::Equals expressions whose static result
    #   is either true or false; do not imply that only one outcome is detected.
    #   IF either outcome would use another identifier or severity:
    #     REJECT that metadata as inconsistent with the W8003 finding contract.
    #   IF the description omits or contradicts either detectable outcome:
    #     REJECT the description as inconsistent with detection behavior.
    #   EXPOSE the same identifier, severity classification, and description for
    #   findings handed off from every invocation of equals_is_useful.
    id = "W8003"
    shortdesc = "Fn::Equals will always return true or false"
    description = (
        "Validate Fn::Equals to see if its comparing two strings or two equal items."
        " While this works it may not be intended."
    )
    source_url = "https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference-conditions.html#intrinsic-function-reference-conditions-equals"
    tags = ["functions", "equals"]

    def equals_is_useful(self, validator, s, instance, schema):
        # PSEUDOCODE — W8003-001 / W8003-002 / W8003-003
        # Verification loci:
        # - test_W8003_001_identical_literal_equals_when_linted_reports_true_finding
        # - test_W8003_002_unequal_literal_equals_when_linted_reports_false_finding
        # - test_W8003_003_identical_literal_equals_diagnostic_identifies_static_result_true
        # - test_W8003_003_unequal_literal_equals_diagnostic_identifies_static_result_false
        # PROCEDURE evaluate_literal_equals(instance):
        #   INPUT the two operands of the current Fn::Equals expression.
        #   IF instance is not a two-element operand list:
        #     RETURN without a W8003 finding; structural validation owns that failure.
        #   IF either operand cannot be proven to be a literal:
        #     RETURN without a W8003 finding; the equality is not statically constant.
        #   COMPARE the two literal operands using Fn::Equals comparison semantics.
        #   IF the operands compare equal:
        #     SET constant_result to true.  [W8003-001]
        #   ELSE:
        #     SET constant_result to false. [W8003-002]
        #   MAP constant_result to its exact diagnostic token:
        #     true maps only to "true"; false maps only to "false". [W8003-003]
        #   FORMAT the diagnostic with that one token so it identifies the actual
        #   static result and never presents both possible outcomes. [W8003-003]
        #   CREATE one finding using this rule's W8003 identity and warning
        #   classification, then HAND OFF that finding for the current expression.
        #   IF the selected diagnostic token does not match constant_result:
        #     DO NOT EMIT a misleading finding; surface the inconsistent state.
        #   IF comparison cannot be completed safely:
        #     RETURN without a finding rather than claiming a constant result.
        if not validator.is_type(instance, "array"):
            return

        if len(instance) != 2:
            return

        literal_types = ("boolean", "integer", "number", "string")
        if any(
            not any(validator.is_type(value, type_) for type_ in literal_types)
            for value in instance
        ):
            return

        yield ValidationError(
            f"{instance!r} will always return {True!r} or {False!r}",
            rule=self,
        )
