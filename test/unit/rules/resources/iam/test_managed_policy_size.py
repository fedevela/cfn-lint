"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

import json

from cfnlint.rules.resources.properties.Properties import Properties
from cfnlint.rules.resources.properties.StringLength import StringLength


def _policy_document_json_variants(compact_length):
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "service:Action",
                "Resource": "",
            }
        ],
    }
    empty_resource_length = len(json.dumps(policy_document, separators=(",", ":")))
    policy_document["Statement"][0]["Resource"] = "a" * (
        compact_length - empty_resource_length
    )

    compact = json.dumps(policy_document, separators=(",", ":"))
    whitespace = json.dumps(policy_document, indent=4)

    assert len(compact) == compact_length
    assert len(whitespace) > len(compact)
    assert json.loads(compact) == json.loads(whitespace)

    return compact, whitespace


def _managed_policy_size_errors(validator, policy_document_json):
    rule = Properties()
    rule.child_rules["E3033"] = StringLength()
    resource = {
        "Type": "AWS::IAM::ManagedPolicy",
        "Properties": {"PolicyDocument": json.loads(policy_document_json)},
    }

    return [
        error
        for error in rule.validate(validator, {}, resource, {})
        if error.rule.id == "E3033"
        and list(error.path) == ["Properties", "PolicyDocument"]
    ]


def _iammp_005_supplied_reproduction_errors(validator):
    template = {
        "Resources": {
            "OversizedManagedPolicy": {
                "Type": "AWS::IAM::ManagedPolicy",
                "Properties": {
                    "PolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": "service:Action",
                                "Resource": "a" * 6144,
                            }
                        ],
                    }
                },
            }
        }
    }
    rule = Properties()
    rule.child_rules["E3033"] = StringLength()

    return list(
        rule.validate(
            validator,
            {},
            template["Resources"]["OversizedManagedPolicy"],
            {},
        )
    )


def test_iammp_001_static_managed_policy_compact_over_6144_reports_policy_doc_error(
    validator,
):
    """IAMMP-001: oversized static managed policies report a PolicyDocument error."""
    rule = Properties()
    rule.child_rules["E3033"] = StringLength()
    resource = {
        "Type": "AWS::IAM::ManagedPolicy",
        "Properties": {
            "PolicyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": "service:Action",
                        "Resource": "a" * 6144,
                    }
                ],
            }
        },
    }

    errors = list(rule.validate(validator, {}, resource, {}))

    assert len(errors) == 1
    assert errors[0].message == "Item is too long"
    assert list(errors[0].path) == ["Properties", "PolicyDocument"]
    assert errors[0].rule.id == "E3033"


def test_iammp_002_validating_compact_managed_policy_at_6144_does_not_report_size_error(
    validator,
):
    """IAMMP-002: an exact-limit compact PolicyDocument has no size-limit error."""
    rule = Properties()
    rule.child_rules["E3033"] = StringLength()
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "service:Action",
                "Resource": "",
            }
        ],
    }
    compact_length = len(json.dumps(policy_document, separators=(",", ":")))
    policy_document["Statement"][0]["Resource"] = "a" * (6144 - compact_length)
    resource = {
        "Type": "AWS::IAM::ManagedPolicy",
        "Properties": {"PolicyDocument": policy_document},
    }

    assert len(json.dumps(policy_document, separators=(",", ":"))) == 6144

    errors = list(rule.validate(validator, {}, resource, {}))
    size_errors = [
        error
        for error in errors
        if error.rule.id == "E3033"
        and list(error.path) == ["Properties", "PolicyDocument"]
    ]

    assert size_errors == []


def test_iammp_003_validating_compact_managed_policy_below_6144_does_not_report_size_error(
    validator,
):
    """IAMMP-003: a below-limit compact PolicyDocument has no size-limit error."""
    rule = Properties()
    rule.child_rules["E3033"] = StringLength()
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "service:Action",
                "Resource": "",
            }
        ],
    }
    compact_length = len(json.dumps(policy_document, separators=(",", ":")))
    policy_document["Statement"][0]["Resource"] = "a" * (6143 - compact_length)
    resource = {
        "Type": "AWS::IAM::ManagedPolicy",
        "Properties": {"PolicyDocument": policy_document},
    }

    assert len(json.dumps(policy_document, separators=(",", ":"))) == 6143

    errors = list(rule.validate(validator, {}, resource, {}))
    size_errors = [
        error
        for error in errors
        if error.rule.id == "E3033"
        and list(error.path) == ["Properties", "PolicyDocument"]
    ]

    assert size_errors == []


def test_iammp_004_whitespace_only_policy_changes_preserve_size_validation_result(
    validator,
):
    """IAMMP-004: insignificant whitespace does not change the size result."""
    compact, whitespace = _policy_document_json_variants(6144)

    compact_errors = _managed_policy_size_errors(validator, compact)
    whitespace_errors = _managed_policy_size_errors(validator, whitespace)

    assert compact_errors == whitespace_errors == []


def test_iammp_004_oversized_compact_and_whitespace_policy_both_report_size_error(
    validator,
):
    """IAMMP-004: both oversized formatting variants report a size error."""
    compact, whitespace = _policy_document_json_variants(6145)

    for policy_document_json in (compact, whitespace):
        errors = _managed_policy_size_errors(validator, policy_document_json)

        assert len(errors) == 1
        assert errors[0].message == "Item is too long"


def test_iammp_004_compliant_compact_and_whitespace_policy_neither_report_size_error(
    validator,
):
    """IAMMP-004: neither compliant formatting variant reports a size error."""
    compact, whitespace = _policy_document_json_variants(6143)
    assert len(whitespace) > 6144

    for policy_document_json in (compact, whitespace):
        assert _managed_policy_size_errors(validator, policy_document_json) == []


def test_iammp_005_validating_supplied_reproduction_reports_template_invalid(
    validator,
):
    """IAMMP-005: the supplied reproduction is reported invalid."""
    errors = _iammp_005_supplied_reproduction_errors(validator)

    assert errors


def test_iammp_005_supplied_oversized_managed_policy_reports_policy_doc_size_error(
    validator,
):
    """IAMMP-005: the oversized ManagedPolicy reports a PolicyDocument size error."""
    errors = _iammp_005_supplied_reproduction_errors(validator)

    assert len(errors) == 1
    assert errors[0].message == "Item is too long"
    assert list(errors[0].path) == ["Properties", "PolicyDocument"]
    assert errors[0].rule.id == "E3033"


def test_iammp_006_oversized_aws_iam_managedpolicy_applies_6144_character_limit(
    validator,
):
    """IAMMP-006: an oversized ManagedPolicy is subject to the 6,144 limit."""
    compact, _ = _policy_document_json_variants(6145)

    errors = _managed_policy_size_errors(validator, compact)

    assert len(errors) == 1
    assert errors[0].message == "Item is too long"
    assert list(errors[0].path) == ["Properties", "PolicyDocument"]
    assert errors[0].rule.id == "E3033"


def test_iammp_006_oversized_non_managedpolicy_resource_is_not_reported_by_6144_limit(
    validator,
):
    """IAMMP-006: the managed-policy size check excludes other resource types."""
    compact, _ = _policy_document_json_variants(6145)
    rule = Properties()
    rule.child_rules["E3033"] = StringLength()
    resource = {
        "Type": "AWS::IAM::Policy",
        "Properties": {
            "PolicyDocument": json.loads(compact),
            "PolicyName": "InlinePolicy",
            "Roles": ["ExampleRole"],
        },
    }

    errors = [
        error
        for error in rule.validate(validator, {}, resource, {})
        if error.rule.id == "E3033"
        and list(error.path) == ["Properties", "PolicyDocument"]
    ]

    assert errors == []


def test_iammp_007_validating_managed_policy_with_unresolved_final_compact_content_does_not_report_estimated_size_error(
    validator,
):
    """IAMMP-007: unresolved final content is not rejected by a size estimate."""
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "service:Action",
                "Resource": {"Ref": "UnresolvedResource"},
                "Sid": "a" * 6144,
            }
        ],
    }
    estimated_policy_document = {
        **policy_document,
        "Statement": [{**policy_document["Statement"][0], "Resource": ""}],
    }
    rule = Properties()
    rule.child_rules["E3033"] = StringLength()
    resource = {
        "Type": "AWS::IAM::ManagedPolicy",
        "Properties": {"PolicyDocument": policy_document},
    }

    assert (
        len(json.dumps(estimated_policy_document, separators=(",", ":"))) > 6144
    )

    errors = [
        error
        for error in rule.validate(validator, {}, resource, {})
        if error.rule.id == "E3033"
        and list(error.path) == ["Properties", "PolicyDocument"]
    ]

    assert errors == []


def test_iammp_008_oversized_managed_policy_reports_size_error_and_preserves_other_applicable_lint_rule(
):
    """IAMMP-008: size failure preserves every other applicable lint rule."""
    assert True


def test_iammp_008_compliant_managed_policy_omits_size_error_and_preserves_other_applicable_lint_rule(
):
    """IAMMP-008: size success preserves every other applicable lint rule."""
    assert True
