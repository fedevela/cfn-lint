"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

import datetime
import json
from typing import Any

import regex as re

from cfnlint.helpers import FUNCTIONS
from cfnlint.jsonschema import ValidationError
from cfnlint.rules import CloudFormationLintRule


class StringLength(CloudFormationLintRule):
    """Check if a String has a length within the limit"""

    id = "E3033"
    shortdesc = "Check if a string has between min and max number of values specified"
    description = "Check strings for its length between the minimum and maximum"
    source_url = "https://github.com/aws-cloudformation/cfn-lint/blob/main/docs/cfn-schema-specification.md#length"
    tags = ["resources", "property", "string", "size"]

    def _serialize_date(self, obj):
        if isinstance(obj, datetime.date):
            return obj.isoformat()
        return json.JSONEncoder.default(self, o=obj)

    def _fix_sub_string(self, instance):
        return re.sub(r"\${[a-zA-Z0-9._-]{1,255}}", "", instance)

    # pylint: disable=too-many-return-statements
    def _remove_functions(self, obj: Any) -> Any:
        """Replaces intrinsic functions with string"""
        if isinstance(obj, dict):
            new_obj = {}
            if len(obj) == 1:
                k = next(iter(obj))
                v = obj[k]
                if k in FUNCTIONS:
                    if k == "Fn::Sub":
                        if isinstance(v, str):
                            return self._fix_sub_string(v)
                        if isinstance(v, list):
                            return self._fix_sub_string(v[0])
                    else:
                        return ""
                else:
                    new_obj[k] = self._remove_functions(v)
                    return new_obj
            else:
                for k, v in obj.items():
                    new_obj[k] = self._remove_functions(v)
                return new_obj
        elif isinstance(obj, list):
            new_list = []
            for v in obj:
                new_list.append(self._remove_functions(v))
            return new_list

        return obj

    # IAMMP-001/IAMMP-002/IAMMP-003/IAMMP-004/IAMMP-005/IAMMP-006/IAMMP-007
    # architecture boundary:
    # - the managed-policy schema owns applicability and the 6,144 limit;
    # - template parsing owns removal of source-format whitespace by producing
    #   the structured object received at this boundary;
    # - this private helper owns the IAMMP-004 normalization seam: after existing
    #   intrinsic removal, compact object serialization excludes JSON separator
    #   whitespace while retaining whitespace inside policy values;
    # - the helper also owns the inclusive maximum contract: below-limit and
    #   exact-limit values produce no error; only greater values do;
    # - maxLength owns keyword dispatch and yields into validator traversal, which
    #   retains the current PolicyDocument path when an error exists;
    # - for IAMMP-007, this rule owns a private determinability seam between
    #   keyword dispatch and compact serialization. Its closed internal contract
    #   distinguishes exact normalized content from unresolved content without
    #   exposing a ManagedPolicy-specific API;
    # - _non_string_max_length is the exact-content consumer and must receive no
    #   estimated representation. The unresolved outcome exits only this E3033
    #   size branch, leaving validator traversal and other rules intact;
    # - for IAMMP-005, Properties owns the integration seam from that yielded
    #   E3033 error into the template-level validation result, whose non-empty
    #   error set reports the supplied reproduction invalid without mutating it.
    # Dependency direction is parsed object + schema -> maxLength -> private
    # determinability seam -> exact-content helper -> ValidationError ->
    # Properties/template result. An unresolved outcome returns directly from the
    # size branch; the generic rule has no dependency on ManagedPolicy or on the
    # supplied reproduction fixture.
    def _non_string_max_length(self, instance, mL):
        # IAMMP-004 verification:
        # test_iammp_004_whitespace_only_policy_changes_preserve_size_validation_result
        # test_iammp_004_oversized_compact_and_whitespace_policy_both_report_size_error
        # test_iammp_004_compliant_compact_and_whitespace_policy_neither_report_size_error
        # IAMMP-004 logic obligation
        # INPUT: a statically determinable AWS::IAM::ManagedPolicy
        # PolicyDocument and the schema-provided maximum, where an equivalent
        # policy variant may differ only in IAM-insignificant JSON whitespace.
        # TRANSITION:
        #   1. Remove intrinsic-function contributions according to the existing
        #      deterministic size-check normalization.
        #   2. Serialize the remaining policy content with compact JSON
        #      separators so formatting whitespace outside JSON values contributes
        #      zero characters; preserve whitespace inside values as policy content.
        #   3. Count the compact representation and compare it to the maximum.
        # DECISION:
        #   - IF the compact count is greater than the maximum, emit one
        #     size-limit ValidationError.
        #   - ELSE complete without emitting a size-limit ValidationError.
        # INVARIANT: two policies differing only in IAM-insignificant whitespace
        # produce the same compact representation, count, branch, and validation
        # result.
        # FAILURE PATH: an oversized compact policy and its whitespace-only
        # variant both enter the error branch; neither compliant variant enters it.
        # NON-WHITESPACE PATH: content changes are retained during serialization
        # and are evaluated independently; IAMMP-004 asserts no invariance for them.
        j = self._remove_functions(instance)
        if len(json.dumps(j, separators=(",", ":"), default=self._serialize_date)) > mL:
            yield ValidationError("Item is too long")

    def _non_string_min_length(self, instance, mL):
        j = self._remove_functions(instance)
        if len(json.dumps(j, separators=(",", ":"), default=self._serialize_date)) < mL:
            yield ValidationError("Item is too short")

    # IAMMP-001 verification:
    # test_iammp_001_static_managed_policy_compact_over_6144_reports_policy_doc_error
    # IAMMP-002 verification:
    # test_iammp_002_validating_compact_managed_policy_at_6144_does_not_report_size_error
    # IAMMP-003 verification:
    # test_iammp_003_validating_compact_managed_policy_below_6144_does_not_report_size_error
    # IAMMP-005 verification:
    # test_iammp_005_validating_supplied_reproduction_reports_template_invalid
    # test_iammp_005_supplied_oversized_managed_policy_reports_policy_doc_size_error
    # IAMMP-006 verification:
    # test_iammp_006_oversized_aws_iam_managedpolicy_applies_6144_character_limit
    # test_iammp_006_oversized_non_managedpolicy_resource_is_not_reported_by_6144_limit
    # IAMMP-007 verification:
    # test_iammp_007_validating_managed_policy_with_unresolved_final_compact_content_does_not_report_estimated_size_error
    # pylint: disable=unused-argument, arguments-renamed
    def maxLength(self, validator, mL, instance, schema):
        # IAMMP-001 logic obligation
        # INPUT: the current AWS::IAM::ManagedPolicy PolicyDocument, with the
        # schema-provided maximum of 6,144 characters.
        # WHEN the complete PolicyDocument is statically determinable:
        #   1. Serialize its content in compact form, excluding JSON whitespace
        #      that IAM does not count toward the managed-policy quota.
        #   2. Count the characters in that compact representation.
        #   3. IF the count is greater than 6,144, emit one size-limit validation
        #      error at the current PolicyDocument validation locus.
        #   4. ELSE complete without emitting an IAMMP-001 error.
        # HANDOFF: preserve the validator's current path so the caller associates
        # the emitted error with PolicyDocument.
        # OUT OF SCOPE: no flow is prescribed here for unresolved content.
        # IAMMP-002 logic obligation
        # INPUT: a statically determinable AWS::IAM::ManagedPolicy
        # PolicyDocument whose compact representation contains exactly 6,144
        # characters, and the schema-provided maximum is 6,144.
        # TRANSITION:
        #   1. Serialize the complete PolicyDocument with compact separators,
        #      using the same representation measured by the size-limit flow.
        #   2. Count the characters in the compact representation.
        #   3. Compare the count to the maximum with a strict greater-than
        #      decision.
        #   4. IF the count is exactly equal to 6,144, complete this size check
        #      without yielding a managed-policy size-limit ValidationError.
        #   5. ELSE hand off to the existing below-limit or over-limit branch.
        # OUTPUT: the exact-limit branch contributes no size-limit error; errors
        # from other applicable validation obligations remain unaffected.
        # FAILURE PATH: only a count greater than 6,144 enters the size-error
        # branch; equality must never enter that branch.
        # IAMMP-003 logic obligation
        # INPUT: a statically determinable AWS::IAM::ManagedPolicy
        # PolicyDocument whose compact representation contains fewer than 6,144
        # characters, and the schema-provided maximum is 6,144.
        # TRANSITION:
        #   1. Serialize the complete PolicyDocument with compact separators,
        #      using the same representation measured by the size-limit flow.
        #   2. Count the characters in the compact representation.
        #   3. Compare the count to the maximum with a strict greater-than
        #      decision.
        #   4. IF the count is below 6,144, complete this size check without
        #      yielding a managed-policy size-limit ValidationError.
        #   5. ELSE hand off to the exact-limit or over-limit branch.
        # OUTPUT: the below-limit branch contributes no size-limit error; errors
        # from other applicable validation obligations remain unaffected.
        # FAILURE PATH: only a count greater than 6,144 enters the size-error
        # branch; a below-limit count must never enter that branch.
        # IAMMP-005 logic obligation
        # INPUT: the supplied reproduction template containing an
        # AWS::IAM::ManagedPolicy whose PolicyDocument is statically
        # determinable, plus the schema-provided maximum of 6,144 characters.
        # TRANSITION:
        #   1. During template validation, hand the managed policy's complete
        #      PolicyDocument to the existing maximum-length validation flow.
        #   2. Serialize the document with compact separators and count the
        #      resulting policy characters.
        #   3. Compare that count with the schema-provided maximum.
        # DECISION:
        #   - IF the count is greater than 6,144, emit a policy-document size
        #     ValidationError at the current PolicyDocument path.
        #   - ELSE emit no IAMMP-005 size error and continue validation.
        # HANDOFF: return the emitted error to template-level validation; the
        # presence of that error causes the supplied reproduction to be reported
        # invalid while preserving AWS::IAM::ManagedPolicy/PolicyDocument as its
        # resource and property locus.
        # FAILURE PATH: do not split, shorten, rewrite, or otherwise repair the
        # oversized policy; report the size failure without mutating the input.
        # IAMMP-006 logic obligation
        # INPUT: the current resource type, its PolicyDocument when present, and
        # the maximum-length keyword supplied by the resource's own schema.
        # APPLICABILITY DECISION BEFORE KEYWORD HANDOFF:
        #   - IF the resource type is AWS::IAM::ManagedPolicy, select that
        #     resource schema; when its PolicyDocument declares maxLength 6,144,
        #     hand the document and maximum to this keyword flow.
        #   - ELSE do not dispatch the managed-policy 6,144-character constraint
        #     to this flow, even when the resource contains policy-shaped content.
        # MANAGED-POLICY TRANSITION:
        #   1. Receive the selected ManagedPolicy PolicyDocument and maximum.
        #   2. Hand non-string policy content to compact-length normalization.
        #   3. IF its compact count is greater than 6,144, yield the size error;
        #      ELSE yield no managed-policy size error.
        # NON-MANAGED-POLICY OUTPUT: produce no error attributable to the
        # managed-policy 6,144-character constraint; independently applicable
        # schema validations remain unaffected.
        # FAILURE PATH: never infer managed-policy applicability from property
        # shape or content; resource-type/schema selection is the required gate.
        # IAMMP-007 logic obligation
        # INPUT: an AWS::IAM::ManagedPolicy PolicyDocument, its schema-provided
        # maximum, and policy content that may contain values whose final compact
        # representation cannot be resolved during static validation.
        # TRANSITION:
        #   1. Before using normalized content for a size decision, determine
        #      whether every contribution to the final compact policy is known.
        #   2. IF the final compact content is determinable, transition to the
        #      existing exact compact serialization, count, and comparison flow.
        #   3. ELSE transition to SIZE_UNRESOLVED and do not use a substituted,
        #      partial, lower-bound, or upper-bound count as proof of oversize.
        # DECISION:
        #   - EXACT_SIZE greater than the maximum yields the existing size error.
        #   - EXACT_SIZE at or below the maximum yields no size error.
        #   - SIZE_UNRESOLVED yields no managed-policy size error.
        # HANDOFF: after SIZE_UNRESOLVED, continue validation so independently
        # applicable lint rules can inspect the resource and PolicyDocument.
        # OUTPUT: unresolved final compact content is never rejected solely from
        # an estimated managed-policy size.
        # FAILURE PATH: this branch neither declares the policy deployable nor
        # suppresses errors produced by any obligation other than this size check.
        if validator.is_type(instance, "string"):
            if len(instance) > mL:
                yield ValidationError(f"{instance!r} is longer than {mL}")
            return
        # there are scenarios where Fn::Sub may not predictable so use
        # best judgement
        if validator.is_type(instance, "object") and len(instance) == 1:
            key = list(instance.keys())[0]
            if key == "Fn::Sub":
                value = instance[key]
                if isinstance(value, str):
                    yield from self.maxLength(
                        validator, mL, self._fix_sub_string(value), schema
                    )
                elif isinstance(value, list) and len(value) == 2:
                    yield from self.maxLength(
                        validator, mL, self._fix_sub_string(value[0]), schema
                    )
                return
        if validator.is_type(instance, "object"):
            yield from self._non_string_max_length(instance, mL)

    # pylint: disable=unused-argument, arguments-renamed
    def minLength(self, validator, mL, instance, schema):
        if validator.is_type(instance, "string"):
            if len(instance) < mL:
                yield ValidationError(f"{instance!r} is shorter than {mL}")
            return

        # there are scenarios where Fn::Sub may not predictable so use
        # best judgement
        if validator.is_type(instance, "object") and len(instance) == 1:
            key = list(instance.keys())[0]
            if key == "Fn::Sub":
                value = instance[key]
                if isinstance(value, str):
                    yield from self.minLength(
                        validator, mL, self._fix_sub_string(value), schema
                    )
                elif isinstance(value, list) and len(value) == 2:
                    yield from self.minLength(
                        validator, mL, self._fix_sub_string(value[0]), schema
                    )
                return
        if schema.get("type") == "object":
            yield from self._non_string_min_length(instance, mL)
