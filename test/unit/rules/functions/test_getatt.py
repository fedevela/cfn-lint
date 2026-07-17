"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from collections import deque

import pytest

from cfnlint.jsonschema import ValidationError
from cfnlint.rules import CfnLintKeyword
from cfnlint.rules.functions.GetAtt import GetAtt


@pytest.fixture(scope="module")
def rule():
    rule = GetAtt()
    yield rule


_template = {
    "Resources": {
        "MyBucket": {"Type": "AWS::S3::Bucket"},
        "MyCodePipeline": {"Type": "AWS::CodePipeline::Pipeline"},
        "DocDBCluster": {"Type": "AWS::DocDB::DBCluster"},
    },
    "Parameters": {
        "MyResourceParameter": {"Type": "String", "Default": "MyBucket"},
        "MyAttributeParameter": {"Type": "String", "AllowedValues": ["Arn"]},
    },
}

_template_with_transform = _template.copy()
_template_with_transform["Transform"] = "AWS::LanguageExtensions"

_gev_literal_map_template = {
    "Transform": "AWS::LanguageExtensions",
    "Resources": {
        "InputQueuea1": {"Type": "AWS::SQS::Queue"},
    },
}

_gev_find_in_map_template = {
    "Transform": "AWS::LanguageExtensions",
    "Mappings": {
        "ResourceNames": {
            "a-1": {"EscapedInput": "a1"},
            "a-2": {"EscapedInput": "a2"},
            "b-1": {"EscapedInput": "b1"},
            "b-2": {"EscapedInput": "b2"},
        }
    },
    "Resources": {
        "InputQueuea1": {"Type": "AWS::SQS::Queue"},
        "InputQueuea2": {"Type": "AWS::SQS::Queue"},
        "InputQueueb1": {"Type": "AWS::SQS::Queue"},
        "InputQueueb2": {"Type": "AWS::SQS::Queue"},
    },
}


@pytest.fixture(scope="module")
def gev_literal_map_getatt_case():
    """GEV-001/GEV-002 integration seam for GetAtt -> Sub -> resource lookup."""
    return {
        "instance": {
            "Fn::GetAtt": [
                {
                    "Fn::Sub": [
                        "InputQueue${EscapedInput}",
                        {"EscapedInput": "a1"},
                    ]
                },
                "Arn",
            ]
        },
        "schema": {"type": "string"},
    }


def _gev_mapped_getatt_case(loop_input):
    return {
        "Fn::GetAtt": [
            {
                "Fn::Sub": [
                    "InputQueue${EscapedInput}",
                    {
                        "EscapedInput": {
                            "Fn::FindInMap": [
                                "ResourceNames",
                                loop_input,
                                "EscapedInput",
                            ]
                        }
                    },
                ]
            },
            "Arn",
        ]
    }


class _Pass(CfnLintKeyword):
    id = "AAAAA"

    def __init__(self) -> None:
        super().__init__(keywords=["*"])

    def validate(self, validator, s, instance, schema):
        return
        yield


class _Fail(CfnLintKeyword):
    id = "BBBBB"

    def __init__(self) -> None:
        super().__init__(keywords=["*"])

    def validate(self, validator, s, instance, schema):
        yield ValidationError("Fail")


@pytest.mark.parametrize(
    "name,instance,schema,template,child_rules,expected",
    [
        (
            "Valid GetAtt with a good attribute",
            {"Fn::GetAtt": ["MyBucket", "Arn"]},
            {"type": "string"},
            _template,
            {},
            [],
        ),
        (
            "Invalid GetAtt with bad attribute",
            {"Fn::GetAtt": ["MyBucket", "foo"]},
            {"type": "string"},
            _template,
            {},
            [
                ValidationError(
                    (
                        "'foo' is not one of ['Arn', 'DomainName', "
                        "'DualStackDomainName', 'RegionalDomainName', 'WebsiteURL'] "
                        "in ['us-east-1']"
                    ),
                    path=deque(["Fn::GetAtt", 1]),
                    schema_path=deque([]),
                    validator="fn_getatt",
                ),
            ],
        ),
        (
            "Invalid GetAtt with bad resource name",
            {"Fn::GetAtt": ["Foo", "bar"]},
            {"type": "string"},
            _template,
            {},
            [
                ValidationError(
                    (
                        "'Foo' is not one of ['MyBucket', "
                        "'MyCodePipeline', 'DocDBCluster']"
                    ),
                    path=deque(["Fn::GetAtt", 0]),
                    schema_path=deque(["enum"]),
                    validator="fn_getatt",
                ),
            ],
        ),
        (
            "Invalid GetAtt with a bad type",
            {"Fn::GetAtt": {"foo": "bar"}},
            {"type": "string"},
            _template,
            {},
            [
                ValidationError(
                    "{'foo': 'bar'} is not of type 'string', 'array'",
                    path=deque(["Fn::GetAtt"]),
                    schema_path=deque(["type"]),
                    validator="fn_getatt",
                ),
            ],
        ),
        (
            "Invalid GetAtt with a bad response type",
            {"Fn::GetAtt": "MyBucket.Arn"},
            {"type": "array"},
            _template,
            {},
            [
                ValidationError(
                    "{'Fn::GetAtt': 'MyBucket.Arn'} is not of type 'array'",
                    path=deque(["Fn::GetAtt"]),
                    schema_path=deque(["type"]),
                    validator="fn_getatt",
                ),
            ],
        ),
        (
            "Invalid GetAtt with a bad response type and multiple types",
            {"Fn::GetAtt": "MyBucket.Arn"},
            {"type": ["array", "object"]},
            _template,
            {},
            [
                ValidationError(
                    "{'Fn::GetAtt': 'MyBucket.Arn'} is not of type 'array', 'object'",
                    path=deque(["Fn::GetAtt"]),
                    schema_path=deque(["type"]),
                    validator="fn_getatt",
                ),
            ],
        ),
        (
            "Valid GetAtt with integer to string",
            {"Fn::GetAtt": "MyCodePipeline.Version"},
            {"type": ["integer"]},
            _template,
            {},
            [],
        ),
        (
            "Valid GetAtt with exception type",
            {"Fn::GetAtt": "DocDBCluster.Port"},
            {"type": ["string"]},
            _template,
            {},
            [],
        ),
        # (
        #    "Invalid GetAtt with integer to string",
        #    {"Fn::GetAtt": "MyCodePipeline.Version"},
        #    {"type": ["integer"]},
        #    {
        #        "strict_types": True,
        #    },
        #    {},
        #    [
        #        ValidationError(
        #            (
        #                "{'Fn::GetAtt': 'MyCodePipeline.Version'} "
        #                "is not of type 'integer'"
        #            ),
        #            path=deque(["Fn::GetAtt"]),
        #            schema_path=deque(["type"]),
        #            validator="fn_getatt",
        #        )
        #    ],
        # ),
        (
            "Valid GetAtt with one good response type",
            {"Fn::GetAtt": "MyBucket.Arn"},
            {"type": ["array", "string"]},
            _template,
            {},
            [],
        ),
        (
            "Valid Ref in GetAtt for resource",
            {"Fn::GetAtt": [{"Ref": "MyResourceParameter"}, "Arn"]},
            {"type": "string"},
            _template_with_transform,
            {},
            [],
        ),
        (
            "Valid Ref in GetAtt for attribute",
            {"Fn::GetAtt": ["MyBucket", {"Ref": "MyAttributeParameter"}]},
            {"type": "string"},
            _template_with_transform,
            {},
            [],
        ),
        (
            "Invalid Ref in GetAtt for attribute",
            {"Fn::GetAtt": ["MyBucket", {"Ref": "MyResourceParameter"}]},
            {"type": "string"},
            _template_with_transform,
            {},
            [
                ValidationError(
                    (
                        "'MyBucket' is not one of ['Arn', 'DomainName', "
                        "'DualStackDomainName', 'RegionalDomainName', "
                        "'WebsiteURL'] in ['us-east-1'] when "
                        "{'Ref': 'MyResourceParameter'} is resolved"
                    ),
                    path=deque(["Fn::GetAtt", 1]),
                    validator="fn_getatt",
                )
            ],
        ),
        (
            "Invalid Ref in GetAtt for attribute",
            {"Fn::GetAtt": [{"Ref": "MyAttributeParameter"}, "Arn"]},
            {"type": "string"},
            _template_with_transform,
            {},
            [
                ValidationError(
                    (
                        "'Arn' is not one of ['MyBucket', "
                        "'MyCodePipeline', 'DocDBCluster'] when "
                        "{'Ref': 'MyAttributeParameter'} is resolved"
                    ),
                    path=deque(["Fn::GetAtt", 0]),
                    schema_path=deque(["enum"]),
                    validator="fn_getatt",
                )
            ],
        ),
        (
            "Valid GetAtt with child rules",
            {"Fn::GetAtt": ["MyBucket", "Arn"]},
            {"type": "string"},
            _template,
            {
                "AAAAA": _Pass(),
                "BBBBB": _Fail(),
                "CCCCC": None,
            },
            [ValidationError("Fail")],
        ),
    ],
    indirect=["template"],
)
def test_validate(name, instance, schema, child_rules, expected, validator, rule):
    rule.child_rules = child_rules
    errs = list(rule.fn_getatt(validator, schema, instance, {}))

    assert errs == expected, f"Test {name!r} got {errs!r}"


@pytest.mark.parametrize("template", [_gev_literal_map_template], indirect=True)
def test_gev_001_language_extensions_accepts_complete_literal_map_sub_as_getatt_resource_name(
    gev_literal_map_getatt_case, validator, rule
):
    """GEV-001: a complete literal-map Fn::Sub resource name emits no E1010."""
    case = gev_literal_map_getatt_case
    rule.child_rules = {}

    assert list(
        rule.fn_getatt(validator, case["schema"], case["instance"], {})
    ) == []


@pytest.mark.parametrize("template", [_gev_literal_map_template], indirect=True)
def test_gev_002_literal_map_sub_resolving_to_input_queue_a1_is_accepted_as_declared_resource(
    gev_literal_map_getatt_case, validator, rule
):
    """GEV-002: literal a1 resolves to the declared InputQueuea1 resource."""
    case = gev_literal_map_getatt_case
    rule.child_rules = {}
    resource_name = case["instance"]["Fn::GetAtt"][0]
    resolutions = list(validator.resolve_value(resource_name))

    assert [value for value, _, _ in resolutions] == ["InputQueuea1"]
    assert list(
        rule.fn_getatt(validator, case["schema"], case["instance"], {})
    ) == []


@pytest.mark.parametrize("template", [_gev_find_in_map_template], indirect=True)
def test_gev_003_two_arg_sub_findinmap_declared_resource_name_is_accepted(
    validator, rule
):
    """GEV-003: LanguageExtensions maps Sub to an accepted resource name."""
    instance = _gev_mapped_getatt_case("a-1")
    resource_name = instance["Fn::GetAtt"][0]
    rule.child_rules = {}

    assert [value for value, _, _ in validator.resolve_value(resource_name)] == [
        "InputQueuea1"
    ]
    assert list(rule.fn_getatt(validator, {"type": "string"}, instance, {})) == []


@pytest.mark.parametrize("template", [_gev_find_in_map_template], indirect=True)
@pytest.mark.parametrize(
    "loop_input,expected_resource_name",
    [
        ("a-1", "InputQueuea1"),
        ("a-2", "InputQueuea2"),
        ("b-1", "InputQueueb1"),
        ("b-2", "InputQueueb2"),
    ],
)
def test_gev_004_foreach_a_1_a_2_b_1_b_2_dynamic_getatt_emits_no_e1010(
    loop_input, expected_resource_name, validator, rule
):
    """GEV-004: the reported loop inputs transition without E1010 findings."""
    instance = _gev_mapped_getatt_case(loop_input)
    resource_name = instance["Fn::GetAtt"][0]
    rule.child_rules = {}

    assert [value for value, _, _ in validator.resolve_value(resource_name)] == [
        expected_resource_name
    ]
    assert list(rule.fn_getatt(validator, {"type": "string"}, instance, {})) == []
