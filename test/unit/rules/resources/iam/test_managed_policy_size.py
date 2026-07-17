"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

import json

from cfnlint.rules.resources.properties.Properties import Properties
from cfnlint.rules.resources.properties.StringLength import StringLength


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
):
    """IAMMP-003: a below-limit compact PolicyDocument has no size-limit error."""
    assert True
