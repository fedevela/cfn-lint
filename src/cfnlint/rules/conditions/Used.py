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
            # ARCHITECTURE [CFNLINT-005, CFNLINT-008]: `Used.match()` remains the
            # compatibility owner for all condition-use classifications. Its
            # stable inbound boundary is the `Template` API: direct references
            # arrive through the existing template searches/raw sections, while
            # resource references arrive through `get_resources()`. Both paths
            # converge here without making this rule depend on language-extension
            # internals or introducing a separate `Fn::ForEach` classifier.
            # PSEUDOCODE [CFNLINT-005, CFNLINT-008] — compatibility input:
            # INPUT the declared conditions and every condition reference found
            # through the existing non-dynamic paths: `Fn::If`, condition-to-
            # condition use, a resource `Condition`, and an output `Condition`.
            # FOR EACH such reference, preserve its complete condition name in
            # the referenced-condition collection; do not require `Fn::ForEach`
            # expansion and do not alter, discard, or synthesize a name.
            # IF no dynamically resolved `Fn::ForEach` reference is present,
            # carry this existing collection unchanged to classification.
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

            # ARCHITECTURE [CFNLINT-001, CFNLINT-002, CFNLINT-003, CFNLINT-004,
            # CFNLINT-006, CFNLINT-007]:
            # `Template.get_resources()` is the integration seam between language
            # expansion and W8001.  This rule owns condition-use classification,
            # but depends only on the transformed resource view: `Condition`
            # remains an ordinary resource field and no iteration-specific port,
            # adapter, or generated-name knowledge belongs in this rule.
            # Get resource's Conditions
            # PSEUDOCODE [CFNLINT-001, CFNLINT-002, CFNLINT-006, CFNLINT-007]:
            # INPUT all resources from the fully transformed template, including
            # resources emitted by nested `Fn::ForEach` expansion.
            # FOR EACH resource with a `Condition`, carry its resolved value into
            # the same referenced-condition collection used by direct resources.
            # COMPARE declared condition names to collected values generically;
            # a matching resolved string marks that declaration used, independent
            # of iteration depth or name. Thus resolved references to each of
            # `ShouldCreateBucket1`, `ShouldCreateBucket2`, and
            # `ShouldCreateBucket3` produce no W8001 for those declarations.
            # IF a declaration has no exact collected match, keep it eligible for
            # the existing W8001 result; do not suppress unrelated conditions.
            # PSEUDOCODE [CFNLINT-003, CFNLINT-004] — generated reference input:
            # FOR EACH transformed resource, inspect its resolved `Condition`.
            # IF the field exists, append that single resolved value to the
            # referenced-condition collection without widening, prefix matching,
            # or propagating use to any other declared condition.
            # IF the field is absent or its generated name was not resolvable,
            # add no generated reference; preserve the declarations' prior state.
            for _, resource_values in cfn.get_resources().items():
                if "Condition" in resource_values:
                    ref_conditions.append(resource_values["Condition"])

            # Get Output Conditions
            for _, output_values in cfn.template.get("Outputs", {}).items():
                if "Condition" in output_values:
                    ref_conditions.append(output_values["Condition"])

            # ARCHITECTURE [CFNLINT-003, CFNLINT-004, CFNLINT-005,
            # CFNLINT-008]: `ref_conditions` is the private integration contract
            # between every reference-producing path above and the single
            # per-declaration classifier below. The contract carries names only;
            # this W8001 boundary owns exact-name association, so direct and
            # transformed inputs share classification without coupling to each
            # other, and every nonmatching declaration remains independently
            # reportable through the existing `RuleMatch` output boundary.
            # Check if the confitions are used
            # PSEUDOCODE [CFNLINT-005, CFNLINT-008] — compatibility result:
            # FOR EACH declaration, compare its complete name with the preserved
            # reference collection independently of every other declaration.
            # IF a direct non-`Fn::ForEach` reference matches, classify that
            # declaration as used and produce no W8001 result for it.
            # ELSE classify it as unused and keep it eligible for its existing
            # W8001 result; a directly used sibling must not suppress this path.
            # OUTPUT the same per-declaration used-versus-unused classifications
            # for any template unaffected by dynamic `Fn::ForEach` resolution.
            # PSEUDOCODE [CFNLINT-003, CFNLINT-004] — exact classification:
            # FOR EACH declared condition, compare its complete name for equality
            # against every collected direct or resolved generated reference.
            # IF an exact match exists, transition only that declaration to used
            # and emit no W8001 result for it.
            # ELSE keep that declaration unused and emit its existing W8001
            # result; a reference matching another declaration changes nothing.
            for condname, _ in conditions.items():
                if condname not in ref_conditions:
                    message = "Condition {0} not used"
                    matches.append(
                        RuleMatch(["Conditions", condname], message.format(condname))
                    )

        return matches
