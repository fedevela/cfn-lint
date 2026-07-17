"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from test.unit.rules import BaseRuleTestCase

from cfnlint.runner import TemplateRunner
from cfnlint.rules.conditions.Used import Used  # pylint: disable=E0401


class TestUsedConditions(BaseRuleTestCase):
    """Test template mapping configurations"""

    def setUp(self):
        """Setup"""
        super(TestUsedConditions, self).setUp()
        self.collection.register(Used())

    success_templates = [
        "test/fixtures/templates/good/generic.yaml",
    ]

    def test_file_positive(self):
        """Test Positive"""
        self.helper_file_positive()

    def test_file_negative(self):
        """Test failure"""
        self.helper_file_negative("test/fixtures/templates/bad/conditions.yaml", 5)

    def _assert_template_has_no_unused_conditions(self, template, expected_condition):
        runner = TemplateRunner("", template, self.config, self.collection)
        self.assertEqual([], list(runner.run()))
        self.assertEqual(
            [expected_condition],
            [
                resource["Condition"]
                for resource in runner.cfn.get_resources().values()
            ],
        )

    def test_cfnlint_001_resolved_foreach_resource_condition_is_used_by_w8001(self):
        """GUID: CFNLINT-001 - resolved generated Condition marks declaration used."""
        self._assert_template_has_no_unused_conditions(
            {
                "Transform": "AWS::LanguageExtensions",
                "Conditions": {"CreateAlpha": {"Fn::Equals": ["a", "a"]}},
                "Resources": {
                    "Fn::ForEach::Resources": [
                        "Name",
                        ["Alpha"],
                        {
                            "${Name}Bucket": {
                                "Type": "AWS::S3::Bucket",
                                "Condition": "Create${Name}",
                            }
                        },
                    ]
                },
            },
            "CreateAlpha",
        )

    def test_cfnlint_006_inner_foreach_condition_survives_outer_expansion_for_w8001(
        self,
    ):
        """GUID: CFNLINT-006 - inner Condition remains used after outer expansion."""
        self._assert_template_has_no_unused_conditions(
            {
                "Transform": "AWS::LanguageExtensions",
                "Conditions": {"DeployDevPrimary": {"Fn::Equals": ["a", "a"]}},
                "Resources": {
                    "Fn::ForEach::Environments": [
                        "Environment",
                        ["Dev"],
                        {
                            "Fn::ForEach::Tiers": [
                                "Tier",
                                ["Primary"],
                                {
                                    "${Environment}${Tier}Bucket": {
                                        "Type": "AWS::S3::Bucket",
                                        "Condition": "Deploy${Environment}${Tier}",
                                    }
                                },
                            ]
                        },
                    ]
                },
            },
            "DeployDevPrimary",
        )

    def test_cfnlint_007_equivalent_iteration_condition_name_is_used_by_w8001(self):
        """GUID: CFNLINT-007 - any resolved declared Condition name is used."""
        self._assert_template_has_no_unused_conditions(
            {
                "Transform": "AWS::LanguageExtensions",
                "Conditions": {"EnableTelemetry": {"Fn::Equals": ["a", "a"]}},
                "Resources": {
                    "Fn::ForEach::Features": [
                        "Feature",
                        ["Telemetry"],
                        {
                            "${Feature}Topic": {
                                "Type": "AWS::SNS::Topic",
                                "Condition": "Enable${Feature}",
                            }
                        },
                    ]
                },
            },
            "EnableTelemetry",
        )
