"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from test.unit.rules import BaseRuleTestCase

from cfnlint.runner import TemplateRunner
from cfnlint.rules.conditions.Used import Used  # pylint: disable=E0401


class TestUsedConditionsCfnLint003004(BaseRuleTestCase):
    """Verify exact W8001 association for generated condition references."""

    def setUp(self):
        """Run W8001 against a template with one matching generated reference."""
        super().setUp()
        self.collection.register(Used())
        runner = TemplateRunner("", self._template(), self.config, self.collection)
        self.matches = list(runner.run())
        self.resource_conditions = [
            resource["Condition"]
            for resource in runner.cfn.get_resources().values()
        ]

    @staticmethod
    def _template():
        return {
            "Transform": "AWS::LanguageExtensions",
            "Conditions": {
                "CreateAlpha": {"Fn::Equals": ["a", "a"]},
                "CreateAlphaExtended": {"Fn::Equals": ["a", "a"]},
            },
            "Resources": {
                "Fn::ForEach::Resources": [
                    "Name",
                    ["Alpha"],
                    {
                        "${Name}Bucket": {
                            "Type": "AWS::S3::Bucket",
                            "Condition": {"Fn::Sub": "Create${Name}"},
                        }
                    },
                ]
            },
        }

    def test_cfnlint_003_resolved_generated_condition_marks_only_exact_declaration_used(
        self,
    ):
        """GUID: CFNLINT-003 - an exact generated match marks only that condition used."""
        self.assertEqual(["CreateAlpha"], self.resource_conditions)
        self.assertNotIn(
            ["Conditions", "CreateAlpha"],
            [match.path for match in self.matches],
        )

    def test_cfnlint_004_unreferenced_nonmatching_condition_remains_w8001_eligible(
        self,
    ):
        """GUID: CFNLINT-004 - a condition without any matching reference remains unused."""
        self.assertEqual(
            [["Conditions", "CreateAlphaExtended"]],
            [match.path for match in self.matches],
        )
        self.assertEqual(
            ["Condition CreateAlphaExtended not used"],
            [match.message for match in self.matches],
        )
