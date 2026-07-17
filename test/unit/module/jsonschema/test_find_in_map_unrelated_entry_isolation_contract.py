"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0

Contracts for isolating four-argument Fn::FindInMap property validation from
unrelated second-level mapping entries.
"""

import json

from cfnlint import lint


def _property_errors(second_level_values, second_level_key="BucketName"):
    template = {
        "Transform": "AWS::LanguageExtensions",
        "Parameters": {"LookupKey": {"Type": "String"}},
        "Mappings": {"BucketConfig": {"Names": second_level_values}},
        "Resources": {
            "Bucket": {
                "Type": "AWS::S3::Bucket",
                "Properties": {
                    "BucketName": {
                        "Fn::FindInMap": [
                            "BucketConfig",
                            "Names",
                            second_level_key,
                            {"DefaultValue": {"Ref": "AWS::NoValue"}},
                        ]
                    }
                },
            }
        },
    }

    return [
        match
        for match in lint(json.dumps(template), regions=["us-east-1"])
        if match.rule.id == "E3012"
    ]


def test_fim_006_s3_bucket_name_ignores_unrelated_array_without_e3012():
    """FIM-006: the supplied S3 unrelated-array reproduction reports no E3012."""
    errors = _property_errors(
        {"NotBucketNameSecondLevelKey": ["unrelated", "values"]}
    )

    assert errors == []


def test_fim_006_adding_incompatible_unrelated_entry_preserves_lookup_result():
    """FIM-006: adding an incompatible sibling leaves validation unchanged."""
    without_sibling = _property_errors({})
    with_sibling = _property_errors({"Unrelated": ["not-a-bucket-name"]})

    assert with_sibling == without_sibling == []


def test_fim_006_removing_incompatible_unrelated_entry_preserves_lookup_result():
    """FIM-006: removing an incompatible sibling leaves validation unchanged."""
    before_removal = _property_errors({"Unrelated": ["not-a-bucket-name"]})
    after_removal = _property_errors({})

    assert before_removal == after_removal == []


def test_fim_006_changing_incompatible_unrelated_entry_preserves_lookup_result():
    """FIM-006: changing an incompatible sibling leaves validation unchanged."""
    first_value = _property_errors({"Unrelated": ["first"]})
    changed_value = _property_errors({"Unrelated": ["second", "third"]})

    assert first_value == changed_value == []


def test_fim_006_static_lookup_validates_only_applicable_heterogeneous_value():
    """FIM-006: only the applicable heterogeneous mapping value is validated."""
    errors = _property_errors(
        {
            "BucketName": "applicable-bucket-name",
            "UnrelatedList": ["not", "applicable"],
            "UnrelatedNumber": 42,
        }
    )

    assert errors == []


def test_fim_008_unresolved_lookup_ignores_incompatible_unrelated_value():
    """FIM-008: an unrelated value alone causes no unresolved-lookup error."""
    errors = _property_errors(
        {"Unrelated": ["not-a-bucket-name"]},
        second_level_key={"Ref": "LookupKey"},
    )

    assert errors == []
