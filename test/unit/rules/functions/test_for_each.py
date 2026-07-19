"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from test.unit.rules import BaseRuleTestCase

from cfnlint.rules.functions.ForEach import ForEach
from cfnlint.runner import TemplateRunner


class TestForEach(BaseRuleTestCase):
    def setUp(self):
        super(TestForEach, self).setUp()
        self.collection.register(ForEach())
        self.success_templates = [
            "test/fixtures/templates/good/functions/foreach.yaml",
        ]

    def test_file_positive(self):
        self.helper_file_positive()

    def test_file_negative_missing_transform(self):
        self.helper_file_negative(
            "test/fixtures/templates/bad/functions/foreach_no_transform.yaml", 3
        )


class TestForEach015TransformRequirement(BaseRuleTestCase):
    def setUp(self):
        super(TestForEach015TransformRequirement, self).setUp()
        self.collection.register(ForEach())

    def _run_fixture(self, filename):
        template = self.load_template(filename)
        runner = TemplateRunner(filename, template, self.config, self.collection)
        return list(runner.run())

    def test_foreach_015_without_transform_reports_e1032_at_resources_outputs_and_nested_loops(
        self,
    ):
        """GUID: FOREACH-015; all three established loop locations report E1032."""
        failures = self._run_fixture(
            "test/fixtures/templates/bad/functions/foreach_no_transform.yaml"
        )
        expected_paths = [
            "Resources/Fn::ForEach::Buckets",
            "Outputs/Fn::ForEach::BucketOutputs",
            "Outputs/Fn::ForEach::BucketOutputs/2/Fn::ForEach::GetAttLoop",
        ]
        self.assertEqual(expected_paths, [failure.path_string for failure in failures])
        self.assertEqual(["E1032"] * 3, [failure.rule.id for failure in failures])
        self.assertEqual(
            [
                (
                    "Missing Transform: Declare the AWS::LanguageExtensions "
                    "Transform globally to enable use of the intrinsic function "
                    f"Fn::ForEach at {path}"
                )
                for path in expected_paths
            ],
            [failure.message for failure in failures],
        )

    def test_foreach_015_without_transform_and_literal_empty_collection_reports_e1032(
        self,
    ):
        """GUID: FOREACH-015; literal [] cannot bypass the missing-transform check."""
        failures = self._run_fixture(
            "test/fixtures/templates/bad/functions/"
            "foreach_no_transform_empty_collection.yaml"
        )
        self.assertEqual(1, len(failures))
        self.assertEqual("E1032", failures[0].rule.id)
        self.assertEqual(
            "Resources/Fn::ForEach::EmptyQueues", failures[0].path_string
        )
        self.assertEqual(
            "Missing Transform: Declare the AWS::LanguageExtensions Transform "
            "globally to enable use of the intrinsic function Fn::ForEach at "
            "Resources/Fn::ForEach::EmptyQueues",
            failures[0].message,
        )

    def test_foreach_015_with_language_extensions_transform_value_reports_no_e1032(
        self,
    ):
        """GUID: FOREACH-015; the scalar transform declaration enables the loop."""
        self.assertEqual(
            [],
            self._run_fixture("test/fixtures/templates/good/functions/foreach.yaml"),
        )

    def test_foreach_015_with_language_extensions_in_transform_list_reports_no_e1032(
        self,
    ):
        """GUID: FOREACH-015; the supported transform list enables the loop."""
        self.assertEqual(
            [],
            self._run_fixture(
                "test/fixtures/templates/good/functions/foreach_transform_list.yaml"
            ),
        )
