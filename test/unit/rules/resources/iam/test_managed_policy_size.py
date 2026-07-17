"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

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
