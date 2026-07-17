"""Tests for non-nested ``Fn::FindInMap`` default resolution."""

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
            "Roles": {"B": {"Source": "Unused"}},
            "Sources": {"Github": {"Names": ["Repository"]}},
        },
        "Resources": {
            "Fn::ForEach::Sources": [
                "Source",
                {
                    "Fn::FindInMap": [
                        "Sources",
                        {
                            "Fn::FindInMap": [
                                "Roles",
                                "A",
                                "Source",
                                {"DefaultValue": "Github"},
                            ]
                        },
                        "Names",
                    ]
                },
                {
                    "${Source}Bucket": {
                        "Type": "AWS::S3::Bucket",
                    }
                },
            ]
        },
    }


def _cfn(template):
    return Template(filename="", template=template, regions=["us-east-1"])


def test_cfnlint_007_non_nested_missing_key_uses_default_and_lint_exits_0():
    """GUID: CFNLINT-007.

    Given a missing mapping key outside a nested Fn::ForEach collection,
    transforming and linting uses DefaultValue and completes with exit code 0.
    """
    template = _template()
    collection_lookup = _ForEachValue.create(
        template["Resources"]["Fn::ForEach::Sources"][1]
    )

    assert collection_lookup.value(_cfn(template)) == ["Repository"]

    transform_matches, transformed = language_extension(_cfn(template))
    lint_matches = lint(json.dumps(template), regions=["us-east-1"])

    assert transform_matches == []
    assert transformed["Resources"] == {
        "RepositoryBucket": {"Type": "AWS::S3::Bucket"}
    }
    assert lint_matches == []
