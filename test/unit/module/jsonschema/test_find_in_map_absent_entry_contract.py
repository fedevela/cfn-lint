"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0

Contracts for an absent-entry four-argument Fn::FindInMap.
"""

import json

from cfnlint import lint
from cfnlint.context import create_context_for_template
from cfnlint.context.context import Transforms
from cfnlint.jsonschema import CfnTemplateValidator
from cfnlint.rules.functions.FindInMap import FindInMap
from cfnlint.template import Template


def _property_errors(default_value):
    template = Template(
        "",
        {"Mappings": {"Map": {"Top": {"Existing": 1}}}},
        regions=["us-east-1"],
    )
    context = create_context_for_template(template).evolve(
        transforms=Transforms(["AWS::LanguageExtensions"])
    )
    validator = CfnTemplateValidator({}, context=context, cfn=template)
    instance = {
        "Fn::FindInMap": [
            "Map",
            "Top",
            "Absent",
            {"DefaultValue": default_value},
        ]
    }

    return list(FindInMap().fn_findinmap(validator, {"type": "integer"}, instance, {}))


def test_fim_003_absent_entry_applies_compatible_concrete_default():
    """FIM-003: an applicable compatible concrete default passes validation."""
    assert _property_errors(default_value=1) == []


def test_fim_004_absent_entry_applies_incompatible_default_and_reports_error():
    """FIM-004: an applicable incompatible concrete default reports its error."""
    errors = _property_errors(default_value="not-an-integer")

    assert len(errors) == 1
    assert errors[0].validator == "fn_findinmap"
    assert "is not of type 'integer'" in errors[0].message


def test_fim_005_absent_entry_applies_no_value_without_property_type_error():
    """FIM-005: an applicable AWS::NoValue retains property-removal semantics."""
    assert _property_errors(default_value={"Ref": "AWS::NoValue"}) == []


def test_fim_005_s3_absent_bucket_name_no_value_default_avoids_e3012():
    """FIM-005: the S3 absent-BucketName reproduction does not report E3012."""
    template = {
        "Transform": "AWS::LanguageExtensions",
        "Mappings": {"BucketConfig": {"Names": {"Existing": "existing-name"}}},
        "Resources": {
            "Bucket": {
                "Type": "AWS::S3::Bucket",
                "Properties": {
                    "BucketName": {
                        "Fn::FindInMap": [
                            "BucketConfig",
                            "Names",
                            "Absent",
                            {"DefaultValue": {"Ref": "AWS::NoValue"}},
                        ]
                    }
                },
            }
        },
    }

    matches = lint(json.dumps(template), regions=["us-east-1"])

    assert "E3012" not in [match.rule.id for match in matches]
