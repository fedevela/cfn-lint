"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from cfnlint._typing import RuleMatches
from cfnlint.rules import CloudFormationLintRule, RuleMatch
from cfnlint.template import Template


class Used(CloudFormationLintRule):
    """Check if Conditions are configured correctly"""

    id = "W8001"
    shortdesc = "Check if Conditions are Used"
    description = "Making sure the conditions defined are used"
    source_url = "https://github.com/aws-cloudformation/cfn-lint"
    tags = ["conditions"]

    def match(self, cfn: Template) -> RuleMatches:
        matches = []
        ref_conditions = []

        conditions = cfn.template.get("Conditions", {})
        if conditions:
            # Get all "If's" that reference a Condition
            iftrees = cfn.search_deep_keys("Fn::If")

            for iftree in iftrees:
                if isinstance(iftree[-1], list):
                    ref_conditions.append(iftree[-1][0])
                else:
                    ref_conditions.append(iftree[-1])

            # Get conditions used by another condition
            condtrees = cfn.search_deep_keys("Condition")

            for condtree in condtrees:
                if condtree[0] == "Conditions":
                    if isinstance(condtree[-1], (str)):
                        ref_conditions.append(condtree[-1])

            # Get resource's Conditions
            # PSEUDOCODE [CFNLINT-001, CFNLINT-006, CFNLINT-007]:
            # INPUT all resources from the fully transformed template, including
            # resources emitted by nested `Fn::ForEach` expansion.
            # FOR EACH resource with a `Condition`, carry its resolved value into
            # the same referenced-condition collection used by direct resources.
            # COMPARE declared condition names to collected values generically;
            # a matching resolved string marks that declaration used, independent
            # of iteration depth or name, while an absent/unresolved match remains
            # eligible for the existing W8001 unused-condition result.
            for _, resource_values in cfn.get_resources().items():
                if "Condition" in resource_values:
                    ref_conditions.append(resource_values["Condition"])

            # Get Output Conditions
            for _, output_values in cfn.template.get("Outputs", {}).items():
                if "Condition" in output_values:
                    ref_conditions.append(output_values["Condition"])

            # Check if the confitions are used
            for condname, _ in conditions.items():
                if condname not in ref_conditions:
                    message = "Condition {0} not used"
                    matches.append(
                        RuleMatch(["Conditions", condname], message.format(condname))
                    )

        return matches
