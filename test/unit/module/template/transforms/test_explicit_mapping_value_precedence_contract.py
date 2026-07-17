"""Tests for explicit ``Fn::FindInMap`` value precedence."""

import json

from cfnlint import lint
from cfnlint.template import Template
from cfnlint.template.transforms._language_extensions import (
    _ForEachValue,
    language_extension,
)


def _template():
    return {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Transform": "AWS::LanguageExtensions",
        "Mappings": {
            "Roles": {"A": {"Source": "Github"}},
            "Sources": {"Github": {"Names": ["Repository"]}},
        },
        "Resources": {
            "Fn::ForEach::Roles": [
                "Role",
                ["A"],
                {
                    "Fn::ForEach::Sources": [
                        "Source",
                        {
                            "Fn::FindInMap": [
                                "Sources",
                                {
                                    "Fn::FindInMap": [
                                        "Roles",
                                        {"Ref": "Role"},
                                        "Source",
                                        {"DefaultValue": "Fallback"},
                                    ]
                                },
                                "Names",
                            ]
                        },
                        {
                            "${Role}${Source}Bucket": {
                                "Type": "AWS::S3::Bucket",
                            }
                        },
                    ]
                },
            ]
        },
    }


def _cfn(template):
    return Template(filename="", template=template, regions=["us-east-1"])


def test_cfnlint_005_explicit_mapping_value_with_default_transforms_to_explicit_value():
    """GUID: CFNLINT-005 - a present mapping value takes precedence over default."""
    template = _template()
    lookup = _ForEachValue.create(
        {
            "Fn::FindInMap": [
                "Roles",
                "A",
                "Source",
                {"DefaultValue": {"Ref": "UndefinedParameter"}},
            ]
        }
    )

    assert lookup.value(_cfn(template)) == "Github"


def test_cfnlint_006_nested_loop_roles_a_source_github_lints_with_exit_code_0():
    """GUID: CFNLINT-006 - the explicit-key reproduction remains lint-clean."""
    template = _template()

    transform_matches, transformed = language_extension(_cfn(template))
    lint_matches = lint(json.dumps(template), regions=["us-east-1"])

    assert transform_matches == []
    assert transformed["Resources"] == {
        "ARepositoryBucket": {"Type": "AWS::S3::Bucket"}
    }
    assert lint_matches == []
