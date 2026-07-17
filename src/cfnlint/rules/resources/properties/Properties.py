"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

import logging
from collections import deque
from typing import Any

from cfnlint.helpers import FUNCTIONS, is_function
from cfnlint.jsonschema import ValidationError, ValidationResult, Validator
from cfnlint.rules.jsonschema.CfnLintJsonSchema import CfnLintJsonSchema
from cfnlint.schema.manager import PROVIDER_SCHEMA_MANAGER

LOGGER = logging.getLogger(__name__)


class Properties(CfnLintJsonSchema):
    """Check Base Resource Configuration"""

    id = "E3002"
    shortdesc = "Resource properties are invalid"
    description = "Making sure that resources properties are properly configured"
    source_url = "https://github.com/aws-cloudformation/cfn-lint/blob/main/docs/cfn-schema-specification.md#properties"
    tags = ["resources"]

    def __init__(self):
        """Init"""
        super().__init__(
            keywords=["Resources/*"],
            all_matches=True,
        )
        self.rule_set = {
            "additionalProperties": "E3002",
            "anyOf": "E3017",
            "properties": "E3002",
            "dependentExcluded": "E3020",
            "dependentRequired": "E3021",
            "required": "E3003",
            "requiredOr": "E3058",
            "requiredXor": "E3014",
            "enum": "E3030",
            "enumCaseInsensitive": "E3030",
            "type": "E3012",
            "minLength": "E3033",
            "maxLength": "E3033",
            "uniqueItems": "E3037",
            "maximum": "E3034",
            "minimum": "E3034",
            "exclusiveMaximum": "E3034",
            "exclusiveMinimum": "E3034",
            "maxItems": "E3032",
            "minItems": "E3032",
            "pattern": "E3031",
            "prefixItems": "E3008",
            "oneOf": "E3018",
            "cfnLint": "E1101",
            "tagging": "E3024",
        }
        self.child_rules = dict.fromkeys(list(self.rule_set.values()))

    def validate(
        self, validator: Validator, _, instance: Any, schema: Any
    ) -> ValidationResult:
        if not validator.is_type(instance, "object"):
            return

        resolved_conditions = {}
        if validator.is_type(instance.get("Condition"), "string"):
            resolved_conditions = {instance.get("Condition"): True}

        validator = validator.evolve(
            context=validator.context.evolve(
                functions=list(FUNCTIONS),
                strict_types=False,
                conditions=validator.context.conditions.evolve(
                    resolved_conditions,
                ),
            ),
            function_filter=validator.function_filter.evolve(
                add_cfn_lint_keyword=True,
            ),
        )

        t = instance.get("Type")
        if not validator.is_type(t, "string"):
            return

        properties = instance.get("Properties", {})
        fn_k, fn_v = is_function(properties)
        if fn_k == "Ref" and fn_v == "AWS::NoValue":
            yield ValidationError(
                # Expected an object, received {"Ref":"AWS::NoValue"}
                message=f"{properties!r} is not of type object",
                path=deque(["Properties", fn_k]),
                rule=self.child_rules.get(self.rule_set.get("type")),  # type: ignore
                validator="type",
            )
            return

        for regions, schema in PROVIDER_SCHEMA_MANAGER.get_resource_schemas_by_regions(
            t, validator.context.regions
        ):
            region_validator = validator.evolve(
                context=validator.context.evolve(
                    regions=regions,
                    path=validator.context.path.evolve(
                        cfn_path=deque(["Resources", t, "Properties"]),
                    ).descend(path="Properties"),
                ),
            )

            region_validator = self.extend_validator(
                region_validator, schema.schema, region_validator.context.evolve()
            )
            # IAMMP-008 verification:
            # test_iammp_008_oversized_managed_policy_reports_size_error_and_preserves_other_applicable_lint_rule
            # test_iammp_008_compliant_managed_policy_omits_size_error_and_preserves_other_applicable_lint_rule
            # IAMMP-008 logic obligation
            # INPUT: an AWS::IAM::ManagedPolicy and the complete set of schema
            # keywords and lint rules applicable to its properties.
            # TRANSITION:
            #   1. Traverse every applicable validation obligation independently;
            #      do not use the managed-policy size result as a traversal gate.
            #   2. Hand PolicyDocument maxLength validation to the E3033 size
            #      rule and retain its zero-or-one size-error result.
            #   3. Continue traversal after that handoff so every other applicable
            #      rule evaluates the same input and retains its own result.
            # DECISION:
            #   - IF E3033 reports an oversized managed policy, yield that size
            #     error and also yield every independently produced lint error.
            #   - ELSE yield no managed-policy size error and still yield every
            #     independently produced lint error.
            # HANDOFF: prepend the resource Properties path to each error without
            # changing its originating rule, message, or relative property path.
            # FAILURE PATH: an individual size pass or failure must neither stop
            # traversal nor suppress, replace, duplicate, or mutate another
            # applicable rule's diagnostic or behavior.
            # OUTPUT: the result stream differs between the two size branches only
            # by presence or absence of the managed-policy size error.
            for err in self._validate(region_validator, properties):
                err.path.appendleft("Properties")
                yield err
