"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from __future__ import annotations

from collections import deque
from typing import Any, Sequence

import regex as re

from cfnlint.helpers import ensure_list, is_types_compatible
from cfnlint.jsonschema import ValidationError, ValidationResult, Validator
from cfnlint.rules.functions._BaseFn import BaseFn, all_types
from cfnlint.schema import PROVIDER_SCHEMA_MANAGER


class GetAtt(BaseFn):
    """Check if GetAtt values are correct"""

    id = "E1010"
    shortdesc = "GetAtt validation of parameters"
    description = (
        "Validates that GetAtt parameters are to valid resources and properties of"
        " those resources"
    )
    source_url = "https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference-getatt.html"
    tags = ["functions", "getatt"]

    def __init__(self) -> None:
        super().__init__("Fn::GetAtt", all_types)

    def schema(self, validator, instance) -> dict[str, Any]:
        # GEV-006 -- complete two-argument Fn::Sub transform boundary:
        # INPUT: the Fn::GetAtt resource-name operand and the template transforms.
        # IF the operand is Fn::Sub [template_string, variable_map]:
        #   IF AWS::LanguageExtensions is declared:
        #     admit Fn::Sub as a string-producing resource-name function;
        #     hand the complete two-element form to normal function validation,
        #     resolution, and declared-resource checking.
        #   ELSE:
        #     do not add Fn::Sub to the admitted resource-name functions;
        #     validate the unadmitted object against the existing string schema;
        #     emit the existing Fn::GetAtt validation finding at operand 0;
        #     stop before resource-name resolution or attribute validation.
        # ELSE preserve the existing resource-name operand validation flow.
        # OUTPUT: the nested form can proceed only across the declared-transform
        # boundary; otherwise it remains rejected without changing Sub semantics.
        # GEV-003 / GEV-004 -- mapped Fn::Sub resource-name validation:
        # INPUT: each Fn::GetAtt composition delivered after LanguageExtensions
        # expands the reported Fn::ForEach for a-1, a-2, b-1, and b-2.
        # REQUIRE AWS::LanguageExtensions; otherwise use the existing function-
        # admission failure path without changing Fn::ForEach or Fn::Sub semantics.
        # FOR EACH delivered composition, in transformed collection order:
        #   read the resource-name operand as complete Fn::Sub [string, variable_map];
        #   admit Fn::Sub as a string-producing resource-name function;
        #   FOR EACH variable-map entry, resolve its value through the shared resolver;
        #     IF the value is Fn::FindInMap and resolves, bind the mapped result;
        #     ELSE preserve the existing malformed/unresolvable-function failure path;
        #   substitute all resolved bindings into the Fn::Sub string;
        #   FOR EACH resulting logical-name candidate:
        #     IF the candidate is a declared resource, hand it to normal attribute
        #     validation and emit no E1010 solely for the Fn::FindInMap binding;
        #     ELSE preserve the existing E1010 unknown-resource failure path.
        # OUTPUT: all four declared-resource candidates continue independently to
        # attribute validation; one iteration's resolution must not affect another.
        # GEV-001 / GEV-002 -- Fn::GetAtt resource-name resolution logic:
        # INPUT: the first Fn::GetAtt operand and the template transform/resource set.
        # IF AWS::LanguageExtensions is declared:
        #   accept a complete, two-element Fn::Sub as a resolvable string operand;
        #   read its template string and variable map without discarding the map;
        #   resolve each mapped literal, then substitute it into the template string;
        #   hand each resulting logical-name candidate to the existing declared-resource
        #   check before attribute validation.
        #   IF a candidate names a declared resource (for example, literal "a1"
        #   produces "InputQueuea1"), continue normal GetAtt validation and emit no
        #   E1010 for the resource-name operand.
        #   ELSE preserve the existing E1010 unresolved/unknown-resource failure path.
        # ELSE preserve the existing resource-name function restrictions.
        # OUT OF SCOPE: nested intrinsic map values, malformed Fn::Sub, and Fn::ForEach;
        # defer those inputs to their existing validation failure paths.
        # GEV-001 / GEV-002 architecture boundary: this schema owns admission of
        # resource-name functions. Resolution remains owned by
        # jsonschema._resolvers_cfn.sub, and declared-resource checking remains owned
        # by _resolve_getatt. The implementation seam is therefore the transform-gated
        # resource_functions contract; no GetAtt-local substitution adapter is needed.
        # GEV-003 / GEV-004 architecture boundary: LanguageExtensions owns Fn::ForEach
        # expansion, while jsonschema._resolvers_cfn.sub owns variable-map expansion
        # through Validator.resolve_value (including Fn::FindInMap). GetAtt depends only
        # on the resolved logical-name candidates delivered through that resolver
        # contract, and validates each candidate independently in _resolve_getatt.
        resource_functions = []
        if validator.context.transforms.has_language_extensions_transform():
            resource_functions = ["Ref", "Fn::Sub"]

        return {
            "type": ["string", "array"],
            "minItems": 2,
            "maxItems": 2,
            "fn_items": [
                {
                    "functions": resource_functions,
                    "schema": {
                        "type": ["string"],
                    },
                },
                {
                    "functions": ["Ref"],
                    "schema": {
                        "type": ["string"],
                    },
                },
            ],
        }

    def _resolve_getatt(
        self,
        validator: Validator,
        key: str,
        value: Any,
        instance: Any,
        s: Any,
        paths: Sequence[Any],
    ) -> ValidationResult:

        # GEV-005 / GEV-010 -- semantic validation after dynamic-name resolution:
        # INPUT: a structurally admitted Fn::GetAtt whose resource-name operand may
        # be a two-argument Fn::Sub, plus the requested attribute operand.
        # FOR EACH resource-name candidate produced by the shared value resolver:
        #   IF resolution cannot determine a candidate, preserve the resolver's
        #   existing validation/error handoff; do not invent a resource identity.
        #   IF the candidate is absent from the declared Resources set (GEV-010):
        #     emit the existing invalid-resource-reference finding at operand 0;
        #     stop processing that candidate before any attribute lookup.
        #   ELSE transition the declared resource and its type to attribute checking.
        #   FOR EACH resolved attribute candidate (GEV-005):
        #     compare it with the declared resource's supported attributes;
        #     IF no supported attribute matches, emit the existing attribute finding
        #     at operand 1 and skip type validation for that attribute candidate;
        #     ELSE continue through the existing GetAtt result-type validation.
        # OUTPUT: when both candidates identify a declared resource and a supported
        # attribute, emit neither an operand-0 nor an operand-1 semantic finding.
        # GEV-005 / GEV-010 architecture boundary: Validator.resolve_value remains
        # the upstream producer of resource-name and attribute candidates;
        # _resolve_getatt owns their semantic interpretation. Its declared-resource
        # port is validator.context.resources, and its attribute-contract port is
        # PROVIDER_SCHEMA_MANAGER plus Resource.get_atts. Keep both checks in this
        # seam so dynamic and literal operands share the same finding paths.
        for resource_name, resource_name_validator, _ in validator.resolve_value(
            value[0]
        ):
            for err in self.fix_errors(
                resource_name_validator.descend(
                    resource_name,
                    {"enum": list(validator.context.resources.keys())},
                    path=key,
                )
            ):
                err.path.append(paths[0])
                if err.instance != value[0]:
                    err.message = err.message + f" when {value[0]!r} is resolved"
                yield err
                break
            else:
                t = validator.context.resources[resource_name].type
                for (
                    regions,
                    schema,
                ) in PROVIDER_SCHEMA_MANAGER.get_resource_schemas_by_regions(
                    t, validator.context.regions
                ):
                    region = regions[0]
                    for attribute_name, _, _ in validator.resolve_value(value[1]):
                        if all(
                            not (bool(re.fullmatch(each, attribute_name)))
                            for each in validator.context.resources[
                                resource_name
                            ].get_atts(region)
                        ):
                            err = ValidationError(
                                (
                                    f"{attribute_name!r} is not one of "
                                    f"{validator.context.resources[resource_name].get_atts(region)!r}"
                                    f" in {regions!r}"
                                ),
                                validator=self.fn.py,
                                path=deque([self.fn.name, 1]),
                            )
                            if attribute_name != value[1]:
                                err.message = (
                                    err.message + f" when {value[1]!r} is resolved"
                                )
                            yield err
                            continue

                        evolved = validator.evolve(schema=s)  # type: ignore
                        evolved.validators = {  # type: ignore
                            "type": validator.validators.get("type"),  # type: ignore
                        }

                        getatts = validator.cfn.get_valid_getatts()
                        t = validator.context.resources[resource_name].type
                        pointer = getatts.match(region, [resource_name, attribute_name])

                        getatt_schema = schema.resolver.resolve_cfn_pointer(pointer)
                        # there is one exception we need to handle.  The resource type
                        # has a mix of types the input is integer and the output
                        # is string.  Since this is the only occurence
                        # we are putting in an exception to it.
                        if (
                            validator.context.resources[resource_name].type
                            == "AWS::DocDB::DBCluster"
                            and attribute_name == "Port"
                        ):
                            getatt_schema = {"type": "string"}

                        if not getatt_schema.get("type") or not s.get("type"):
                            continue

                        schema_types = ensure_list(getatt_schema.get("type"))
                        types = ensure_list(s.get("type"))

                        # GetAtt type checking is strict.
                        # It must match in all cases
                        if any(t in ["boolean", "integer", "boolean"] for t in types):
                            # this should be switched to validate the value of the
                            # property if it was available
                            continue
                        if is_types_compatible(types, schema_types, True):
                            continue

                        reprs = ", ".join(repr(type) for type in types)
                        yield ValidationError(
                            (f"{instance!r} is not of type {reprs}"),
                            validator=self.fn.py,
                            path=deque([self.fn.name]),
                            schema_path=deque(["type"]),
                        )

    def fn_getatt(
        self, validator: Validator, s: Any, instance: Any, schema: Any
    ) -> ValidationResult:
        errs = list(super().validate(validator, s, instance, schema))
        if errs:
            yield from iter(errs)
            return

        key, value = self.key_value(instance)
        paths: list[int | None] = [0, 1]
        if validator.is_type(value, "string"):
            paths = [None, None]
            value = value.split(".", 1)

        errs = list(
            self._resolve_getatt(
                self.validator(validator), key, value, instance, s, paths
            )
        )
        if errs:
            yield from iter(errs)
            return

        keyword = validator.context.path.cfn_path_string
        for rule in self.child_rules.values():
            if rule is None:
                continue
            if keyword in rule.keywords or "*" in rule.keywords:  # type: ignore
                yield from rule.validate(validator, s, value, s)  # type: ignore
