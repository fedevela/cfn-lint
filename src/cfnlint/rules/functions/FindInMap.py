"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from __future__ import annotations

from collections import deque
from typing import Any

from cfnlint.jsonschema import ValidationError, ValidationResult, Validator
from cfnlint.rules.functions._BaseFn import BaseFn, singular_types


class FindInMap(BaseFn):
    """Check if FindInMap values are correct"""

    id = "E1011"
    shortdesc = "FindInMap validation of configuration"
    description = "Making sure the function is a list of appropriate config"
    source_url = "https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference-findinmap.html"
    tags = ["functions", "findinmap"]

    def __init__(self) -> None:
        super().__init__(
            "Fn::FindInMap", ("array",) + singular_types, resolved_rule="W1034"
        )

    def schema(self, validator: Validator, instance: Any) -> dict[str, Any]:
        scalar_schema = {
            "functions": [
                "Fn::FindInMap",
                "Ref",
            ],
            "schema": {
                "type": ["string"],
            },
        }

        schema = {
            "type": "array",
            "minItems": 3,
            "maxItems": 3,
            "fn_items": [
                scalar_schema,
                scalar_schema,
                scalar_schema,
            ],
        }

        # Architecture boundary — GUID: E1011-001, E1011-002
        # This schema owns the accepted FindInMap shape.  Condition-specific
        # diagnostics for that shape belong to fn_findinmap at the delegation
        # seam with BaseFn, rather than to the shared maxItems validator.

        if validator.context.transforms.has_language_extensions_transform():
            scalar_schema["functions"] = [
                "Fn::FindInMap",
                "Fn::Join",
                "Fn::Sub",
                "Fn::If",
                "Fn::Select",
                "Fn::Length",
                "Fn::ToJsonString",
                "Ref",
            ]
            schema["maxItems"] = 4
            # The fourth item is owned by the Language Extensions option
            # contract; it is not an additional FindInMap lookup level.
            schema["fn_items"] = [
                scalar_schema,
                scalar_schema,
                scalar_schema,
                {
                    "functions": [],
                    "schema": {
                        "findinmap_parameters": True,
                        "type": ["object"],
                        "properties": {
                            "DefaultValue": {
                                "default_value": True,
                            }
                        },
                        "additionalProperties": False,
                        "required": ["DefaultValue"],
                    },
                },
            ]

        return schema

    def _default_value(
        self, validator: Validator, s: Any, instance: Any, schema: Any
    ) -> ValidationResult:
        validator = validator.evolve(
            context=validator.context.evolve(
                functions=["Ref"],
            ),
        )
        yield from validator.descend(
            instance,
            {
                "type": ("array",) + singular_types,
            },
        )

    def fn_findinmap(
        self, validator: Validator, s: Any, instance: Any, schema: Any
    ) -> ValidationResult:
        # GUID: E1011-001, E1011-002
        key, value = self.key_value(instance)
        has_language_extensions = (
            validator.context.transforms.has_language_extensions_transform()
        )
        is_overlong = isinstance(value, list) and (
            len(value) > (4 if has_language_extensions else 3)
            or (
                has_language_extensions
                and len(value) == 4
                and isinstance(value[3], str)
            )
        )
        if is_overlong:
            yield ValidationError(
                "FindInMap supports no more than two lookup levels",
                path=deque([key]),
                schema_path=deque(["maxItems"]),
                validator=self.fn.py,
            )
            return

        if has_language_extensions:
            # we have to use a special validator for this
            # as we don't want DefaultValue: !Ref AWS::NoValue
            # is valid
            mapping_validator = validator.extend(
                validators={
                    "default_value": self._default_value,
                },
            )(validator.schema)
            validator = mapping_validator.evolve(
                context=validator.context.evolve(
                    resources={},
                ),
                cfn=validator.cfn,
                function_filter=validator.function_filter,
                resolver=validator.resolver,
            )
            yield from super().validate(validator, s, instance, schema)
            return

        validator = validator.evolve(
            context=validator.context.evolve(
                resources={},
            )
        )
        yield from super().validate(validator, s, instance, schema)
