"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from copy import copy
from typing import Any

import cfnlint.data.schemas.other.resources
import cfnlint.data.schemas.other.step_functions
import cfnlint.helpers
from cfnlint.jsonschema import ValidationError, ValidationResult, Validator
from cfnlint.rules.jsonschema.CfnLintJsonSchema import CfnLintJsonSchema, SchemaDetails
from cfnlint.schema.resolver import RefResolver


def _load_definition_substitution_keys(validator: Validator) -> frozenset[str]:
    path = list(validator.context.path.path)
    if path[-2:] != ["Properties", "Definition"]:
        return frozenset()

    value: Any = validator.cfn.template
    for part in [*path[:-1], "DefinitionSubstitutions"]:
        if not isinstance(value, Mapping) or part not in value:
            return frozenset()
        value = value[part]

    if not isinstance(value, Mapping):
        return frozenset()

    return frozenset(key for key in value if isinstance(key, str))


def _string_contains_declared_substitution(
    value: Any, declared_keys: frozenset[str]
) -> bool:
    if not isinstance(value, str) or not declared_keys:
        return False

    parameters = cfnlint.helpers.REGEX_SUB_PARAMETERS.findall(value)
    if not parameters:
        return False

    referenced_keys = [
        key for parameter in parameters for key in parameter.split(",")
    ]
    return all(key and key in declared_keys for key in referenced_keys)


def _retain_non_deferred_failure(
    error: ValidationError, declared_keys: frozenset[str]
) -> ValidationError | None:
    if _string_contains_declared_substitution(error.instance, declared_keys):
        return None

    if not error.context:
        return error

    retained_context = []
    context_changed = False
    for child_error in error.context:
        retained_error = _retain_non_deferred_failure(child_error, declared_keys)
        if retained_error is None:
            context_changed = True
            continue
        if retained_error is not child_error:
            context_changed = True
        retained_context.append(retained_error)

    if not retained_context:
        return None
    if not context_changed:
        return error

    retained_error = copy(error)
    retained_error.context = retained_context
    for child_error in retained_context:
        child_error.parent = retained_error
    return retained_error


class StateMachineDefinition(CfnLintJsonSchema):
    id = "E3601"
    shortdesc = "Validate the structure of a StateMachine definition"
    description = (
        "Validate the Definition or DefinitionString inside a "
        "AWS::StepFunctions::StateMachine resource"
    )
    source_url = "https://docs.aws.amazon.com/step-functions/latest/dg/amazon-states-language-state-machine-structure.html"
    tags = ["resources", "statemachine"]

    def __init__(self):
        super().__init__(
            keywords=[
                "Resources/AWS::StepFunctions::StateMachine/Properties/Definition",
                # https://github.com/aws-cloudformation/cfn-lint/issues/3518
                # Resources/AWS::StepFunctions::StateMachine/Properties/DefinitionString
            ],
            schema_details=SchemaDetails(
                cfnlint.data.schemas.other.step_functions, "statemachine.json"
            ),
            all_matches=True,
        )

        store = {
            "definition": self.schema,
        }

        self.resolver = RefResolver.from_schema(self.schema, store=store)

    def _fix_message(self, err: ValidationError) -> ValidationError:
        if len(err.path) > 1:
            err.message = f"{err.message} at {'/'.join(err.path)!r}"
        for i, c_err in enumerate(err.context):
            err.context[i] = self._fix_message(c_err)
        return err

    def validate(
        self, validator: Validator, keywords: Any, instance: Any, schema: dict[str, Any]
    ) -> ValidationResult:
        declared_keys = _load_definition_substitution_keys(validator)

        # First time child rules are configured against the rule
        # so we can run this now
        add_path_to_message = False
        if validator.is_type(instance, "string"):
            try:
                step_validator = validator.evolve(
                    context=validator.context.evolve(
                        functions=[],
                    ),
                    resolver=self.resolver,
                    schema=self.schema,
                )
                instance = json.loads(instance)
                add_path_to_message = True
            except json.JSONDecodeError:
                return
        else:
            step_validator = validator.evolve(
                resolver=self.resolver,
                schema=self.schema,
            )

        for err in step_validator.iter_errors(instance):
            err = _retain_non_deferred_failure(err, declared_keys)
            if err is None:
                continue
            if add_path_to_message:
                err = self._fix_message(err)
            if not err.validator.startswith("fn_") and err.validator not in ["cfnLint"]:
                err.rule = self

            yield self._clean_error(err)
