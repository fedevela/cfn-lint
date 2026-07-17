"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

import datetime
import json
from typing import Any

import regex as re

from cfnlint.helpers import FUNCTIONS, ensure_list, is_function
from cfnlint.jsonschema import ValidationError
from cfnlint.rules import CloudFormationLintRule


_MANAGED_POLICY_DOCUMENT_PATH = (
    "Resources",
    "AWS::IAM::ManagedPolicy",
    "Properties",
    "PolicyDocument",
)
_MANAGED_POLICY_WHITESPACE = str.maketrans("", "", " \t\r\n")


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

    def _non_string_max_length(self, instance, mL):
        j = self._remove_functions(instance)
        if len(json.dumps(j, separators=(",", ":"), default=self._serialize_date)) > mL:
            yield ValidationError("Item is too long")

    def _non_string_min_length(self, instance, mL):
        j = self._remove_functions(instance)
        if len(json.dumps(j, separators=(",", ":"), default=self._serialize_date)) < mL:
            yield ValidationError("Item is too short")

    def _serialize_managed_policy_document(self, instance: Any) -> str:
        """Compactly serialize while excluding IAM quota whitespace."""
        if isinstance(instance, str):
            return json.dumps(instance.translate(_MANAGED_POLICY_WHITESPACE))
        if isinstance(instance, dict):
            items = (
                f"{self._serialize_managed_policy_document(key)}:"
                f"{self._serialize_managed_policy_document(value)}"
                for key, value in instance.items()
            )
            return f"{{{','.join(items)}}}"
        if isinstance(instance, list):
            values = (
                self._serialize_managed_policy_document(value)
                for value in instance
            )
            return f"[{','.join(values)}]"
        return json.dumps(
            instance,
            separators=(",", ":"),
            default=self._serialize_date,
        )

    def _managed_policy_document_length(self, instance: Any) -> int:
        instance = self._remove_functions(instance)
        if isinstance(instance, str):
            return len(instance.translate(_MANAGED_POLICY_WHITESPACE))
        return len(self._serialize_managed_policy_document(instance))

    # pylint: disable=unused-argument, arguments-renamed
    def maxLength(self, validator, mL, instance, schema):
        # ARCHITECTURE: GUID MPOL-001, MPOL-002, MPOL-003, MPOL-004
        # Ownership remains in this E3033 maxLength callback: Properties supplies
        # the provider-schema limit and dispatches this keyword to StringLength.
        # The managed-policy specialization is bounded by the canonical
        # validator.context.path.cfn_path for PolicyDocument; every other locus
        # must continue into the generic branches below. The specialization may
        # depend only on that path contract, the existing non-string
        # normalization/serialization seam, and the existing ValidationError
        # channel. The block-scalar reproduction enters through this same seam;
        # its E3001 envelope remains owned by Configuration, with no reverse
        # dependency from this property rule. Do not introduce an IAM-rule
        # dependency, reproduction-specific adapter, or new public API.
        # PSEUDOCODE: GUID MPOL-001, MPOL-002, MPOL-003, MPOL-004
        # INPUT: the current validation locus, PolicyDocument value, and maxLength.
        # IF the locus is AWS::IAM::ManagedPolicy.Properties.PolicyDocument:
        #   NORMALIZE the document through the existing intrinsic-function and
        #   compact-serialization flow used for non-string length validation.
        #   SET measured_length to the count of serialized characters excluding
        #   exactly space, tab, carriage return, and line feed.                 [MPOL-001]
        #   (Documents differing only by those characters therefore transition
        #   to the same measured_length and the same validation outcome.)       [MPOL-001]
        #   IF measured_length <= 6144 (including below and exact boundary):
        #     RETURN without a size-related E3033.                              [MPOL-002]
        #     IF the input is the supplied AWS Load Balancer Controller JSON
        #     policy represented by a YAML block scalar:
        #       PRESERVE the policy value and formatting; HAND OFF no size error
        #       to the enclosing validation flow.                              [MPOL-004]
        #   ELSE (measured_length > 6144):
        #     YIELD the existing maxLength ValidationError for E3033 and RETURN.[MPOL-003]
        # ELSE:
        #   CONTINUE through the existing generic string/function/object branches.
        if tuple(validator.context.path.cfn_path) == _MANAGED_POLICY_DOCUMENT_PATH:
            if self._managed_policy_document_length(instance) > mL:
                yield ValidationError("Item is too long")
            return

        if validator.is_type(instance, "string"):
            if len(instance) > mL:
                yield ValidationError(f"{instance!r} is longer than {mL}")
            return
        # there are scenarios where Fn::Sub may not predictable so use
        # best judgement
        key, value = is_function(instance)
        if key is not None:
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
        if "object" in ensure_list(schema.get("type")):
            yield from self._non_string_max_length(instance, mL)

    # pylint: disable=unused-argument, arguments-renamed
    def minLength(self, validator, mL, instance, schema):
        if validator.is_type(instance, "string"):
            if len(instance) < mL:
                yield ValidationError(f"{instance!r} is shorter than {mL}")
            return

        # there are scenarios where Fn::Sub may not predictable so use
        # best judgement
        key, value = is_function(instance)
        if key is not None:
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

        if "object" in ensure_list(schema.get("type")):
            yield from self._non_string_min_length(instance, mL)
