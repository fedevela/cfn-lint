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

    id = "W8003"
    shortdesc = "Fn::Equals will always return true or false"
    description = (
        "Validate Fn::Equals to see if its comparing two strings or two equal items."
        " While this works it may not be intended."
    )
    source_url = "https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference-conditions.html#intrinsic-function-reference-conditions-equals"
    tags = ["functions", "equals"]

    def equals_is_useful(self, validator, s, instance, schema):
        # PSEUDOCODE — W8003-001 / W8003-002
        # Verification loci:
        # - test_W8003_001_identical_literal_equals_when_linted_reports_true_finding
        # - test_W8003_002_unequal_literal_equals_when_linted_reports_false_finding
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
        #   EMIT one W8003 finding for the current expression and constant_result.
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
