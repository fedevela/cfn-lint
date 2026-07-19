"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0

Verification coverage for the Fn::ForEach declaration contract.
"""

from unittest import TestCase

from cfnlint.decode import convert_dict
from cfnlint.template import Template
from cfnlint.template.transforms._language_extensions import language_extension


class TestForEachDeclarationContract(TestCase):
    def _template(self, declaration):
        return Template(
            filename="foreach-declaration-contract.yaml",
            template=convert_dict(
                {
                    "Transform": "AWS::LanguageExtensions",
                    "Resources": {
                        "ExistingBucket": {"Type": "AWS::S3::Bucket"},
                        "Fn::ForEach::DeclarationContract": declaration,
                    },
                }
            ),
            regions=["us-east-1"],
        )

    def _assert_transform_error(self, declaration, diagnostic):
        matches, transformed = language_extension(self._template(declaration))

        self.assertIsNone(transformed)
        self.assertEqual(["E0001"], [match.rule.id for match in matches])
        self.assertIn(diagnostic, matches[0].message)

    def test_foreach_010_non_list_declaration_transform_reports_three_element_list_error(
        self,
    ):
        """GUID: FOREACH-010; a declaration must be a three-element list."""
        self._assert_transform_error(
            "not-a-list",
            "Fn::ForEach values must be a list of 3 elements",
        )

    def test_foreach_010_two_element_declaration_transform_reports_three_element_list_error(
        self,
    ):
        """GUID: FOREACH-010; a two-element declaration remains invalid."""
        self._assert_transform_error(
            ["Identifier", []],
            "Fn::ForEach values must be a list of 3 elements",
        )

    def test_foreach_010_four_element_declaration_transform_reports_three_element_list_error(
        self,
    ):
        """GUID: FOREACH-010; a four-element declaration remains invalid."""
        self._assert_transform_error(
            ["Identifier", [], {}, "unexpected"],
            "Fn::ForEach values must be a list of 3 elements",
        )

    def test_foreach_011_non_empty_collection_with_non_object_output_transform_reports_output_type_error(
        self,
    ):
        """GUID: FOREACH-011; non-empty loops require an object output."""
        self._assert_transform_error(
            ["Identifier", ["Value"], []],
            "Output must be a dict",
        )

    def test_foreach_011_empty_collection_with_non_object_output_transform_reports_output_type_error(
        self,
    ):
        """GUID: FOREACH-011; zero iterations cannot bypass output validation."""
        self._assert_transform_error(
            ["Identifier", [], []],
            "Output must be a dict",
        )

    def test_foreach_010_011_empty_collection_with_object_output_transform_succeeds_with_zero_iterations(
        self,
    ):
        """GUIDs: FOREACH-010, FOREACH-011; a valid empty loop expands nothing."""
        matches, transformed = language_extension(
            self._template(
                [
                    "Identifier",
                    [],
                    {
                        "Generated${Identifier}": {
                            "Type": "AWS::SQS::Queue"
                        }
                    },
                ]
            )
        )

        self.assertEqual([], matches)
        self.assertIsNotNone(transformed)
        self.assertEqual(
            {"ExistingBucket": {"Type": "AWS::S3::Bucket"}},
            transformed["Resources"],
        )
