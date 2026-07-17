"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0

Contracts for an existing-entry four-argument Fn::FindInMap.
"""

from cfnlint.context import create_context_for_template
from cfnlint.context.context import Transforms
from cfnlint.jsonschema import CfnTemplateValidator
from cfnlint.rules.functions.FindInMap import FindInMap
from cfnlint.template import Template


def _property_errors(selected_value, default_value):
    template = Template(
        "",
        {"Mappings": {"Map": {"Top": {"Second": selected_value}}}},
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
            "Second",
            {"DefaultValue": default_value},
        ]
    }

    return list(FindInMap().fn_findinmap(validator, {"type": "integer"}, instance, {}))


def test_fim_001_existing_compatible_selected_value_passes_property_validation():
    """FIM-001: an existing compatible selected value passes validation."""
    assert _property_errors(selected_value=1, default_value=2) == []


def test_fim_002_existing_incompatible_selected_value_reports_property_error():
    """FIM-002: an existing incompatible selected value reports its error."""
    errors = _property_errors(selected_value="not-an-integer", default_value=2)

    assert len(errors) == 1
    assert errors[0].validator == "fn_findinmap"
    assert "is not of type 'integer'" in errors[0].message


def test_fim_007_existing_entry_ignores_incompatible_unused_default_value():
    """FIM-007: an incompatible unused default does not cause an error."""
    assert _property_errors(selected_value=1, default_value=[]) == []


def test_fim_007_same_existing_value_with_different_defaults_has_same_result():
    """FIM-007: changing an unused default does not change validation."""
    list_default_errors = _property_errors(selected_value=1, default_value=[])
    string_default_errors = _property_errors(
        selected_value=1, default_value="not-an-integer"
    )

    assert list_default_errors == string_default_errors == []
