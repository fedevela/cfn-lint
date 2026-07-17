"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from __future__ import annotations

import json
from typing import Any

import cfnlint.data.schemas.other.resources
import cfnlint.data.schemas.other.step_functions
import cfnlint.helpers
from cfnlint.jsonschema import ValidationError, ValidationResult, Validator
from cfnlint.rules.jsonschema.CfnLintJsonSchema import CfnLintJsonSchema, SchemaDetails
from cfnlint.schema.resolver import RefResolver


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
                "Resources/AWS::StepFunctions::StateMachine/Properties",
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

        definition_keys = ["Definition"]
        if not validator.cfn.has_serverless_transform():
            definition_keys.append("DefinitionString")

        # First time child rules are configured against the rule
        # so we can run this now
        for k in definition_keys:
            value = instance.get(k)
            if not value:
                continue

            # ARCHITECTURE CONTRACT: CFNLINT-001, CFNLINT-002, CFNLINT-003
            # Ownership: intrinsic validators own Fn::Join shape and result typing;
            # this rule owns ASL structure only for directly inspectable definitions.
            # Boundary: classify DefinitionString before constructing step_validator,
            # parsing JSON, or entering the ASL schema validation loop below.
            # Dependency direction: this rule may consume the validator's intrinsic
            # classification, but ASL validation must not inspect generated output.
            # Integration seam: an opaque generated string exits at this point with
            # intrinsic diagnostics preserved and no structural diagnostics added.
            # PSEUDOCODE CONTRACT: CFNLINT-001, CFNLINT-002, CFNLINT-003
            # INPUT: the selected definition key/value and its template context.
            # IF key is DefinitionString AND value is an Fn::Join expression:
            #   HAND OFF Fn::Join shape and string-output checks to intrinsic validation.
            #   MARK the generated string as not directly inspectable by ASL validation.
            #   SKIP ASL object validation; EMIT neither an object-type E1022
            #   (CFNLINT-001) nor missing StartAt/States E3601 (CFNLINT-002).
            # ELSE IF value is literal JSON text:
            #   PARSE it; on parse failure, stop structural validation without E3601.
            #   On parse success, validate the resulting ASL object normally.
            # ELSE:
            #   VALIDATE the directly inspectable definition object normally.
            # FAILURE: malformed Fn::Join remains reportable by intrinsic validation;
            #   diagnostics for inspectable definitions and other properties are preserved.
            # OUTPUT: if no independent diagnostic exists, the reproduction completes
            #   validation successfully (CFNLINT-003).
            # PSEUDOCODE COMPATIBILITY CONTRACT: CFNLINT-004, CFNLINT-005,
            #   CFNLINT-006
            # LOGIC OBLIGATION (CFNLINT-004):
            #   IF the selected definition is directly inspectable:
            #     ENTER the established ASL schema-validation path below.
            #     FOR EACH structural error, preserve its path/rule attribution and
            #       EMIT the established diagnostic.
            # LOGIC OBLIGATION (CFNLINT-005):
            #   IF DefinitionString is intrinsic-generated and therefore opaque:
            #     SKIP only this rule's ASL inspection for that generated value.
            #     RETURN control to the enclosing validation flow so independent
            #       resource-property validators can emit sibling diagnostics.
            # LOGIC OBLIGATION (CFNLINT-006):
            #   IF the exact opaque DefinitionString branch does not apply:
            #     FOLLOW the pre-existing literal-string or object path unchanged.
            #     PRESERVE parsing, substitutions, error cleanup, and diagnostic output.
            # FAILURE PATHS:
            #   A structural failure in an inspectable definition remains reportable.
            #   A sibling-property failure remains reportable after opaque-value bypass.
            #   No branch changes outcomes outside the opaque DefinitionString case.
            function, _ = cfnlint.helpers.is_function(value)
            if k == "DefinitionString" and function == "Fn::Join":
                continue

            add_path_to_message = False
            if validator.is_type(value, "string"):
                try:
                    step_validator = validator.evolve(
                        context=validator.context.evolve(
                            functions=[],
                        ),
                        resolver=self.resolver,
                        schema=self.schema,
                    )
                    value = json.loads(value)
                    add_path_to_message = True
                except json.JSONDecodeError:
                    return
            else:
                step_validator = validator.evolve(
                    resolver=self.resolver,
                    schema=self.schema,
                )

            substitutions = []
            props_substitutions = instance.get("DefinitionSubstitutions", {})
            if validator.is_type(props_substitutions, "object"):
                substitutions = list(props_substitutions.keys())

            for err in step_validator.iter_errors(value):
                if validator.is_type(err.instance, "string"):
                    if (
                        err.instance.replace("${", "").replace("}", "").strip()
                        in substitutions
                    ):
                        continue
                if add_path_to_message:
                    err = self._fix_message(err)

                err.path.appendleft(k)
                if not err.validator.startswith("fn_") and err.validator not in [
                    "cfnLint"
                ]:
                    err.rule = self

                yield self._clean_error(err)
