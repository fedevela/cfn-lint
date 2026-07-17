"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from __future__ import annotations

import json
from collections import deque
from typing import Any, Iterator

import regex as re

from cfnlint.helpers import (
    AVAILABILITY_ZONES,
    PSEUDOPARAMS,
    REGEX_SUB_PARAMETERS,
    REGIONS,
    is_function,
)
from cfnlint.jsonschema import ValidationError, Validator
from cfnlint.jsonschema._typing import ResolutionResult
from cfnlint.jsonschema._utils import equal


def unresolvable(validator: Validator, instance: Any) -> ResolutionResult:
    return
    yield


def ref(validator: Validator, instance: Any) -> ResolutionResult:
    if not isinstance(instance, (str, dict)):
        return

    for instance, instance_validator, _ in validator.resolve_value(instance):
        if validator.is_type(instance, "string"):
            # if the ref is to pseudo-parameter or parameter we can validate the values
            for v, c in instance_validator.context.ref_value(instance):
                yield v, instance_validator.evolve(context=c), None
            return


# Existing-entry architecture (FIM-001, FIM-002, FIM-007):
# - This resolver owns result applicability: an existing mapping entry excludes the
#   four-argument fallback from the ResolutionResult stream.
# - Mapping.find_in_map owns selected-value retrieval; the evolved Validator context
#   below is the integration seam to receiving-property validation.
# - The receiving-property validator owns compatibility errors. It must receive only
#   the selected value and its mapping path, never the unused DefaultValue.
# Dependency direction: mapping lookup -> resolver applicability -> property validator.
# Absent-entry architecture (FIM-003, FIM-004, FIM-005):
# - find_in_map owns the statically resolved no-entry decision and is the only locus
#   that may promote DefaultValue from fallback candidate to applicable result.
# - _find_in_map_default is the adapter into the ResolutionResult contract; its
#   evolved value_path preserves the default's source identity for downstream errors.
# - BaseFn receiving-property validation owns concrete compatibility: compatible
#   defaults pass there (FIM-003), while incompatible defaults fail there (FIM-004).
# - AWS::NoValue remains owned by the existing intrinsic/conditional-removal
#   machinery. This seam must not coerce it to a concrete property type (FIM-005).
# Dependency direction: mapping lookup -> applicability -> default-result adapter ->
# conditional removal / receiving-property validation.
def _find_in_map_default(validator: Validator, default_value: Any) -> ResolutionResult:
    fn_k, fn_v = is_function(default_value)
    if fn_k == "Ref" and fn_v == "AWS::NoValue":
        return

    for value, v, _ in validator.resolve_value(default_value):
        yield value, v.evolve(
            context=v.context.evolve(
                path=v.context.path.evolve(
                    value_path=deque([4, "DefaultValue"])
                )
            ),
        ), None


def find_in_map(validator: Validator, instance: Any) -> ResolutionResult:
    if not validator.is_type(instance, "array"):
        return
    if len(instance) not in [3, 4]:
        return

    default_value = None
    default_value_found = False
    if len(instance) == 4:
        options = instance[3]
        if validator.is_type(options, "object"):
            if "DefaultValue" in options:
                default_value_found = True
                default_value = options["DefaultValue"]

    if not default_value_found and not validator.context.mappings.maps:
        if validator.context.mappings.is_transform:
            return
        yield None, validator, ValidationError(
            (
                f"{instance[0]!r} is not one of "
                f"{list(validator.context.mappings.maps.keys())!r}"
            ),
            path=deque([0]),
        )
    elif default_value_found and not validator.context.mappings.maps:
        if validator.context.mappings.is_transform:
            yield from _find_in_map_default(validator, default_value)
            return

    mappings = list(validator.context.mappings.maps.keys())
    results = []
    found_valid_combination = False
    k, v = is_function(instance[0])
    if k == "Ref" and v in PSEUDOPARAMS:
        if default_value_found:
            yield from _find_in_map_default(validator, default_value)
        return
    for map_name, map_v, _ in validator.resolve_value(instance[0]):
        if not validator.is_type(map_name, "string"):
            continue

        if all(not (equal(map_name, each)) for each in mappings):
            if not default_value_found:
                results.append(
                    (
                        None,
                        map_v,
                        ValidationError(
                            f"{map_name!r} is not one of {mappings!r}",
                            path=deque([0]),
                        ),
                    )
                )
            continue

        if validator.context.mappings.maps[map_name].is_transform:
            continue

        k, v = is_function(instance[2])
        if k == "Ref" and v in PSEUDOPARAMS:
            continue

        k, v = is_function(instance[1])
        if k == "Ref" and v in PSEUDOPARAMS:
            if isinstance(instance[2], str):
                found_top_level_key = False
                found_second_key = False
                for top_level_key, top_values in validator.context.mappings.maps[
                    map_name
                ].keys.items():
                    if v == "AWS::AccountId":
                        if not re.match("^[0-9]{12}$", top_level_key):
                            continue
                    elif v == "AWS::Region":
                        if top_level_key not in REGIONS:
                            continue
                    found_top_level_key = True
                    for second_level_key, second_v, _ in validator.resolve_value(
                        instance[2]
                    ):
                        if second_level_key in top_values.keys:
                            for value in validator.context.mappings.maps[
                                map_name
                            ].find_in_map(
                                top_level_key,
                                second_level_key,
                            ):
                                found_valid_combination = True
                                found_second_key = True
                                yield (
                                    value,
                                    validator.evolve(
                                        context=validator.context.evolve(
                                            path=validator.context.path.evolve(
                                                value_path=deque(
                                                    [
                                                        "Mappings",
                                                        map_name,
                                                        top_level_key,
                                                        second_level_key,
                                                    ]
                                                )
                                            )
                                        )
                                    ),
                                    None,
                                )

                if not found_top_level_key:
                    yield None, validator, ValidationError(
                        (
                            f"{instance[1]!r} is not a "
                            f"first level key for mapping {map_name!r}"
                        ),
                        path=deque([1]),
                    )
                elif not found_second_key:
                    yield None, validator, ValidationError(
                        (
                            f"{instance[2]!r} is not a "
                            "second level key when "
                            f"{instance[1]!r} is resolved "
                            f"for mapping {map_name!r}"
                        ),
                        path=deque([2]),
                    )
            continue

        for top_level_key, top_v, _ in validator.resolve_value(instance[1]):
            if validator.is_type(top_level_key, "integer"):
                top_level_key = str(top_level_key)
            if not validator.is_type(top_level_key, "string"):
                continue

            top_level_keys = list(validator.context.mappings.maps[map_name].keys.keys())
            if all(not (equal(top_level_key, each)) for each in top_level_keys):
                if not default_value_found:
                    results.append(
                        (
                            None,
                            top_v,
                            ValidationError(
                                (
                                    f"{top_level_key!r} is not one of "
                                    f"{top_level_keys!r} for mapping "
                                    f"{map_name!r}"
                                ),
                                path=deque([1]),
                            ),
                        )
                    )
                continue

            if (
                not top_level_key
                or validator.context.mappings.maps[map_name]
                .keys[top_level_key]
                .is_transform
            ):
                continue

            top_v = validator.evolve(
                context=top_v.context.evolve(resolve_pseudo_parameters=False)
            )
            for second_level_key, second_v, err in top_v.resolve_value(instance[2]):
                if validator.is_type(second_level_key, "integer"):
                    second_level_key = str(second_level_key)
                if not validator.is_type(second_level_key, "string"):
                    continue
                second_level_keys = list(
                    validator.context.mappings.maps[map_name]
                    .keys[top_level_key]
                    .keys.keys()
                )
                if all(
                    not (equal(second_level_key, each)) for each in second_level_keys
                ):
                    if not default_value_found:
                        results.append(
                            (
                                None,
                                second_v,
                                ValidationError(
                                    (
                                        f"{second_level_key!r} is not "
                                        f"one of {second_level_keys!r} "
                                        f"for mapping {map_name!r} and "
                                        f"key {top_level_key!r}"
                                    ),
                                    path=deque([2]),
                                ),
                            )
                        )
                    continue

                # Existing-entry resolution pseudocode (FIM-001, FIM-002, FIM-007):
                # INPUT: resolved map_name, top_level_key, second_level_key, and
                # an optional declared DefaultValue from a four-argument lookup.
                # WHEN all three keys select an existing mapping entry:
                #   1. Mark the existing-entry branch as the applicable result.
                #   2. Read each selected value from that entry and hand it to the
                #      receiving property's validator with its mapping value path.
                #   3. If the selected value is compatible, emit no property error
                #      (FIM-001); otherwise preserve the receiving property's
                #      applicable validation error for that value (FIM-002).
                #   4. Do not resolve, yield, or validate DefaultValue, because the
                #      fallback branch was not taken (FIM-007).
                # OUTPUT: results depend only on the selected mapping value, so
                # changing an unused DefaultValue cannot change them (FIM-007).
                # FAILURE/HANDOFF: absent or statically unresolved entries leave
                # this branch and are handled by their separate resolver paths.
                found_valid_combination = True

                for value in validator.context.mappings.maps[map_name].find_in_map(
                    top_level_key,
                    second_level_key,
                ):
                    yield (
                        value,
                        validator.evolve(
                            context=validator.context.evolve(
                                path=validator.context.path.evolve(
                                    value_path=deque(
                                        [
                                            "Mappings",
                                            map_name,
                                            top_level_key,
                                            second_level_key,
                                        ]
                                    )
                                )
                            )
                        ),
                        None,
                    )

    if found_valid_combination:
        return

    # Absent-entry default applicability pseudocode (FIM-003, FIM-004, FIM-005):
    # INPUT: a LanguageExtensions four-argument lookup, its resolved lookup
    # components, the no-entry outcome, and the declared DefaultValue.
    # PRECONDITION: classify an entry as absent only after every lookup component
    # needed for that decision resolves statically; an unresolved component must
    # stop without making DefaultValue applicable.
    # WHEN no existing entry was selected and DefaultValue is declared:
    #   1. Transition DefaultValue from fallback candidate to applicable result.
    #   2. Resolve it while preserving the DefaultValue source path, then hand each
    #      result to the receiving property's validator.
    #   3. If the result is AWS::NoValue, preserve its property-removal sentinel;
    #      treat the receiving property as absent and emit no property-type error
    #      (FIM-005), including no E3012 for the S3 BucketName reproduction.
    #   4. Otherwise, validate the concrete result against the receiving property:
    #      emit no error when compatible (FIM-003), or preserve the applicable
    #      property-validation error when incompatible (FIM-004).
    # FAILURE: if the applicable default itself cannot resolve, do not invent a
    # concrete result; preserve the resolver's unresolved-result behavior.
    # OUTPUT: only the applicable default branch reaches property validation.
    if default_value_found:
        yield from _find_in_map_default(validator, default_value)
        return

    yield from iter(results)


def get_azs(validator: Validator, instance: Any) -> ResolutionResult:
    if not isinstance(instance, (str, dict)):
        return

    for instance, v, _ in validator.resolve_value(instance):
        if v.is_type(instance, "string"):
            if instance == "":
                for region in v.context.regions:
                    yield (
                        AVAILABILITY_ZONES.get(region),
                        v,
                        None,
                    )
            # if the ref is to pseudo-parameter or parameter we can validate the values
            elif instance in AVAILABILITY_ZONES:
                yield AVAILABILITY_ZONES.get(instance), v, None


def _join_expansion(validator: Validator, instances: Any) -> Iterator[Any]:
    if len(instances) == 0:
        return

    if len(instances) == 1:
        for value, _, _ in validator.resolve_value(instances[0]):
            if not isinstance(value, (str, int, float, bool)):
                raise ValueError(f"Incorrect value type for {value!r}")
            yield [value]
        return

    for value, _, _ in validator.resolve_value(instances[0]):
        if not isinstance(value, (str, int, float, bool)):
            raise ValueError(f"Incorrect value type for {value!r}")
        for values in _join_expansion(validator, instances[1:]):
            yield [value] + values


def join(validator: Validator, instance: Any) -> ResolutionResult:
    # quick validations
    if not validator.is_type(instance, "array"):
        return
    if not len(instance) == 2:
        return

    for delimiter, delimiter_v, _ in validator.resolve_value(instance[0]):
        if not delimiter_v.is_type(delimiter, "string"):
            continue
        for values, values_v, _ in validator.resolve_value(instance[1]):
            if not values_v.is_type(values, "array"):
                continue
            try:
                for value in _join_expansion(values_v, values):
                    yield delimiter.join([str(v) for v in value]), values_v, None
            except (ValueError, TypeError):
                return


def select(validator: Validator, instance: Any) -> ResolutionResult:
    # quick validations
    if not validator.is_type(instance, "array"):
        return
    if not len(instance) == 2:
        return

    # get the values from the list
    indexes = validator.resolve_value(instance[0])
    objs = validator.resolve_value(instance[1])

    for i, _, _ in indexes:
        for obj, obj_v, _ in objs:
            try:
                i = int(i)
            except ValueError:
                continue
            if not validator.is_type(obj, "array"):
                continue
            if len(obj) <= i:
                continue
            yield from obj_v.resolve_value(obj[i])


def split(validator: Validator, instance: Any) -> ResolutionResult:
    if not validator.is_type(instance, "array"):
        return
    if not len(instance) == 2:
        return

    for delimiter, _, _ in validator.resolve_value(instance[0]):
        for source_string, source_v, _ in validator.resolve_value(instance[1]):
            if not source_v.is_type(delimiter, "string"):
                continue
            if not source_v.is_type(source_string, "string"):
                continue

            yield source_string.split(delimiter), source_v, None


def _sub_parameter_expansion(
    validator: Validator, parameters: dict[str, Any]
) -> Iterator[dict[str, Any]]:
    parameters = parameters.copy()
    if len(parameters) == 0:
        yield {}
        return

    if len(parameters) == 1:
        for key, value in parameters.items():
            for resolved_value, _, _ in validator.resolve_value(value):
                yield {key: resolved_value}
        return

    key = list(parameters.keys())[0]
    value = parameters.pop(key)
    for resolved_value, _, _ in validator.resolve_value(value):
        for values in _sub_parameter_expansion(validator, parameters):
            yield dict({key: resolved_value}, **values)


def _sub_string(validator: Validator, string: str) -> ResolutionResult:
    sub_regex = re.compile(r"(\${([^!].*?)})")

    def _replace(matchobj):
        nonlocal validator
        for value, c in validator.context.ref_value(matchobj.group(2).strip()):
            if not isinstance(value, (str, int, float, bool)):
                raise ValueError(f"Parameter {matchobj.group(2)!r} has wrong type")

            validator = validator.evolve(
                context=validator.context.evolve(
                    ref_values=c.ref_values,
                )
            )
            return str(value)
        raise ValueError(f"No matches for {matchobj.group(2)!r}")

    try:
        yield re.sub(sub_regex, _replace, string), validator, None
    except ValueError:
        return


def sub(validator: Validator, instance: Any) -> ResolutionResult:
    if not (
        validator.is_type(instance, "array") or validator.is_type(instance, "string")
    ):
        return

    if validator.is_type(instance, "array"):
        if len(instance) != 2:
            return

        string = instance[0]
        parameters = instance[1]
        if not validator.is_type(string, "string"):
            return
        if not validator.is_type(parameters, "object"):
            return

        sub_parameters = REGEX_SUB_PARAMETERS.findall(string)
        for parameter in sub_parameters:
            if parameter in parameters:
                continue
            if "." in parameter:
                parameters[parameter] = {"Fn::GetAtt": parameter}
            else:
                parameters[parameter] = {"Ref": parameter}

        for resolved_parameters in _sub_parameter_expansion(validator, parameters):
            resolved_validator = validator.evolve(
                context=validator.context.evolve(
                    ref_values=resolved_parameters,
                )
            )
            yield from _sub_string(resolved_validator, string)

        return

    # its a string
    sub_parameters = REGEX_SUB_PARAMETERS.findall(instance)
    parameters = {}
    for parameter in sub_parameters:
        if "." in parameter:
            parameters[parameter] = {"Fn::GetAtt": parameter}
        else:
            parameters[parameter] = {"Ref": parameter}
    for resolved_parameters in _sub_parameter_expansion(validator, parameters):
        resolved_validator = validator.evolve(
            context=validator.context.evolve(
                ref_values=resolved_parameters,
            )
        )
        yield from _sub_string(resolved_validator, instance)
        # yield from _sub_string(validator, instance)


def if_(validator: Validator, instance: Any) -> ResolutionResult:
    if not validator.is_type(instance, "array"):
        return

    if len(instance) != 3:
        return

    for i in [1, 2]:
        for value, v, err in validator.resolve_value(instance[i]):
            yield (
                value,
                v.evolve(
                    context=v.context.evolve(
                        path=v.context.path.evolve(value_path=deque([i])),
                    ),
                ),
                err,
            )


def to_json_string(validator: Validator, instance: Any) -> ResolutionResult:
    for value, v, err in validator.resolve_value(instance):
        yield json.dumps(value), v, err


# not all functions need to be resolved.  These functions
# allow us to pull up values from nested functions
# allowing us to test the possible values against the schema
fn_resolvers: dict[str, Any] = {
    "Fn::Base64": unresolvable,
    "Fn::Cidr": unresolvable,
    "Fn::FindInMap": find_in_map,
    "Fn::ForEach": unresolvable,
    "Fn::GetAtt": unresolvable,
    "Fn::GetAZs": get_azs,
    "Fn::ImportValue": unresolvable,
    "Fn::If": if_,
    "Fn::Join": join,
    "Fn::Select": select,
    "Fn::Split": split,
    "Fn::Sub": sub,
    "Fn::Transform": unresolvable,
    "Fn::ToJsonString": to_json_string,
    "Fn::Equals": unresolvable,
    "Fn::Or": unresolvable,
    "Fn::And": unresolvable,
    "Fn::Not": unresolvable,
    "Condition": unresolvable,
    "Fn::Length": unresolvable,
    "Ref": ref,
}
