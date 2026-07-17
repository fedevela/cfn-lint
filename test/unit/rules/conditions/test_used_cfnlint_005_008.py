"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from test.unit.rules import BaseRuleTestCase

from cfnlint.runner import TemplateRunner
from cfnlint.rules.conditions.Used import Used  # pylint: disable=E0401


class TestUsedConditionsCfnLint005008(BaseRuleTestCase):
    """Preserve W8001 classifications outside dynamic Fn::ForEach references."""

    def setUp(self):
        """Register W8001 for each compatibility test."""
        super().setUp()
        self.collection.register(Used())

    def _run_rule(self, template):
        runner = TemplateRunner("", template, self.config, self.collection)
        return list(runner.run())

    def test_cfnlint_005_direct_condition_reference_outside_foreach_remains_used_without_w8001(
        self,
    ):
        """GUID: CFNLINT-005 - a direct reference remains used without W8001."""
        matches = self._run_rule(
            {
                "Conditions": {"CreateBucket": {"Fn::Equals": ["a", "a"]}},
                "Resources": {
                    "Bucket": {
                        "Type": "AWS::S3::Bucket",
                        "Condition": "CreateBucket",
                    }
                },
            }
        )

        self.assertEqual([], matches)

    def test_cfnlint_008_template_without_dynamic_foreach_condition_references_preserves_existing_classifications(
        self,
    ):
        """GUID: CFNLINT-008 - unaffected used/unused classifications persist."""
        matches = self._run_rule(
            {
                "Conditions": {
                    "UsedByIf": {"Fn::Equals": ["a", "a"]},
                    "UsedByCondition": {"Fn::Equals": ["a", "a"]},
                    "ConditionConsumer": {"Condition": "UsedByCondition"},
                    "UsedByResource": {"Fn::Equals": ["a", "a"]},
                    "UsedByOutput": {"Fn::Equals": ["a", "a"]},
                    "UnusedCondition": {"Fn::Equals": ["a", "a"]},
                },
                "Resources": {
                    "Bucket": {
                        "Type": "AWS::S3::Bucket",
                        "Condition": "UsedByResource",
                        "Properties": {
                            "BucketName": {
                                "Fn::If": ["UsedByIf", "example-a", "example-b"]
                            }
                        },
                    }
                },
                "Outputs": {
                    "BucketName": {
                        "Condition": "UsedByOutput",
                        "Value": {"Ref": "Bucket"},
                    }
                },
            }
        )

        self.assertEqual(
            [
                ["Conditions", "ConditionConsumer"],
                ["Conditions", "UnusedCondition"],
            ],
            [match.path for match in matches],
        )

    def test_cfnlint_008_unaffected_mixed_template_keeps_direct_use_and_unused_w8001_eligibility(
        self,
    ):
        """GUID: CFNLINT-008 - direct use stays used and genuine non-use stays eligible."""
        matches = self._run_rule(
            {
                "Conditions": {
                    "DirectlyUsed": {"Fn::Equals": ["a", "a"]},
                    "GenuinelyUnused": {"Fn::Equals": ["a", "a"]},
                },
                "Outputs": {
                    "Result": {
                        "Condition": "DirectlyUsed",
                        "Value": "created",
                    }
                },
            }
        )

        self.assertEqual(
            [["Conditions", "GenuinelyUnused"]],
            [match.path for match in matches],
        )
        self.assertEqual(
            ["Condition GenuinelyUnused not used"],
            [match.message for match in matches],
        )
