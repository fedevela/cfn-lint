"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

import cfnlint.data.schemas.other.resources
import cfnlint.data.schemas.other.step_functions
import cfnlint.helpers
from cfnlint.jsonschema import ValidationError, ValidationResult, Validator
from cfnlint.rules.jsonschema.CfnLintJsonSchema import CfnLintJsonSchema, SchemaDetails
from cfnlint.schema.resolver import RefResolver


if TYPE_CHECKING:
    from typing import TypedDict

    class _TaskResourceSubstitutionScope(TypedDict):
        """GEV-001..005: resource-local inputs for the ARN exemption seam."""

        # GEV-002, GEV-004: binds lookup to the definition's owning resource.
        logical_resource_id: str
        # GEV-001..003: exact keys are authoritative; values remain opaque.
        # GEV-005: entries are lookup inputs only; they do not exempt concrete
        # Task.Resource values from the nested ASL ARN-pattern contract.
        definition_substitutions: Mapping[str, Any]


class StateMachineDefinition(CfnLintJsonSchema):
    id = "E3601"
    shortdesc = "Validate the structure of a StateMachine definition"
    description = (
        "Validate the Definition or DefinitionString inside a "
        "AWS::StepFunctions::StateMachine resource"
    )
    source_url = "https://docs.aws.amazon.com/step-functions/latest/dg/amazon-states-language-state-machine-structure.html"
    tags = ["resources", "statemachine"]

    _DEFINITION_SUBSTITUTION = re.compile(r"\$\{([^{}]+)\}")

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

    def _get_definition_substitutions(self, validator: Validator) -> Mapping[str, Any]:
        """Return substitutions owned by the state machine being validated."""
        path = validator.context.path.path
        if (
            len(path) < 4
            or path[0] != "Resources"
            or path[2] != "Properties"
            or path[-1] != "Definition"
        ):
            return {}

        resources = validator.cfn.template.get("Resources", {})
        if not isinstance(resources, Mapping):
            return {}

        resource = resources.get(path[1], {})
        if not isinstance(resource, Mapping):
            return {}

        properties = resource.get("Properties", {})
        if not isinstance(properties, Mapping):
            return {}

        substitutions = properties.get("DefinitionSubstitutions", {})
        if not isinstance(substitutions, Mapping):
            return {}

        return substitutions

    def _is_declared_task_resource(
        self,
        err: ValidationError,
        definition: Any,
        substitutions: Mapping[str, Any],
    ) -> bool:
        """Whether an ARN pattern error is for a locally declared placeholder."""
        if err.validator != "pattern" or not err.path or err.path[-1] != "Resource":
            return False

        value = definition
        try:
            for part in err.path:
                value = value[part]
        except (KeyError, IndexError, TypeError):
            return False

        if not isinstance(value, str):
            return False

        match = self._DEFINITION_SUBSTITUTION.fullmatch(value)
        return match is not None and match.group(1) in substitutions

    def validate(
        self, validator: Validator, keywords: Any, instance: Any, schema: dict[str, Any]
    ) -> ValidationResult:
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

        # GEV-001, GEV-002, GEV-003, GEV-004, GEV-005 contract -- declared Task
        # Resource substitution gate:
        #
        # OWNERSHIP / DEPENDENCY:
        #   this rule assembles _TaskResourceSubstitutionScope from the outer
        #   CloudFormation validator before delegating to the nested ASL validator
        #
        # INPUTS:
        #   inline_definition := instance
        #   containing_resource := resource named by validator.context.path
        #   local_substitutions := containing_resource.Properties
        #       .DefinitionSubstitutions when it is a mapping; otherwise empty
        #
        # FOR EACH Task.Resource reached while validating inline_definition:
        #   IF Resource is exactly the established `${Name}` placeholder form:
        #       placeholder_name := the text between `${` and `}`
        #       IF local_substitutions contains an exact key equal to placeholder_name:
        #           mark only this Resource occurrence as a declared placeholder
        #           do not resolve or inspect the declaration value; a supported
        #               CloudFormation intrinsic expression remains opaque
        #           bypass the concrete ARN pattern for this occurrence, then
        #               continue all remaining state-machine validation
        #       ELSE:
        #           apply the concrete ARN pattern normally and preserve E3601
        #   ELSE:
        #       apply the existing Resource validation without an exemption
        #
        # GEV-005 -- malformed concrete Task.Resource preservation:
        #   concrete_resource := a Resource that is not exactly a declared
        #       `${Name}` placeholder under the decision flow above
        #   IF concrete_resource fails the existing ARN pattern:
        #       preserve the pattern ValidationError for that Resource occurrence
        #       attach this rule when required by the existing error handoff
        #       yield the cleaned E3601 error to the caller
        #   IF local_substitutions contains unrelated entries:
        #       do not change concrete_resource classification or error flow
        #
        # GEV-006 -- independent state-machine error preservation:
        #   FOR EACH validation_error produced for inline_definition:
        #       IF validation_error is the ARN-pattern failure for exactly one
        #           locally declared Task.Resource placeholder:
        #           suppress only validation_error
        #           continue with the next nested validation error; do not stop,
        #               return, or mark inline_definition globally valid
        #       ELSE:
        #           preserve validation_error regardless of whether another error
        #               in the same definition was suppressed
        #           normalize its message and rule ownership through the existing
        #               E3601 handoff
        #           yield it to the caller
        #
        # GEV-007 -- unrelated lint behavior preservation:
        #   exemption_scope := one E3601 ARN-pattern error for one inline
        #       Task.Resource occurrence
        #   do not mutate the template, resource properties, validator context,
        #       configured rule set, or errors produced by another rule
        #   after this E3601 invocation completes:
        #       return control normally to the lint-rule dispatcher
        #       allow every unrelated resource, property, and configured rule to
        #           follow its existing validation path
        #       preserve each unrelated outcome without filtering, rewriting, or
        #           replacing it because a declared placeholder was accepted
        #
        # ISOLATION / FAILURE RULES:
        #   never consult or merge substitutions from another state machine
        #   never accept a different, partial, or case-variant placeholder name
        #   never extend this exemption beyond inline Task.Resource occurrences
        #   missing/malformed local substitutions fail closed to normal validation
        substitutions = self._get_definition_substitutions(validator)
        for err in step_validator.iter_errors(instance):
            if self._is_declared_task_resource(err, instance, substitutions):
                continue
            if add_path_to_message:
                err = self._fix_message(err)
            if not err.validator.startswith("fn_") and err.validator not in ["cfnLint"]:
                err.rule = self

            yield self._clean_error(err)
