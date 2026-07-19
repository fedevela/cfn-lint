"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from unittest import TestCase

from cfnlint.decode import convert_dict
from cfnlint.template import Template
from cfnlint.template.transforms._language_extensions import language_extension


class TestIssue107ForEachCollectionContracts(TestCase):
    fixture = "test/fixtures/templates/issues/issue_107_foreach_contracts.yaml"

    def _template(self, candidates):
        return convert_dict(
            {
                "Transform": "AWS::LanguageExtensions",
                "Mappings": {"AccountMap": candidates},
                "Resources": {
                    "Seed": {"Type": "AWS::SNS::Topic"},
                    "Fn::ForEach::Values": [
                        "Value",
                        {
                            "Fn::FindInMap": [
                                "AccountMap",
                                {"Ref": "AWS::AccountId"},
                                "Values",
                            ]
                        },
                        {
                            "Result&{Value}": {
                                "Type": "AWS::SNS::Topic",
                                "Properties": {"DisplayName": {"Ref": "Value"}},
                            }
                        },
                    ],
                },
            }
        )

    def _transform(self, source):
        return language_extension(
            Template(filename=self.fixture, template=source, regions=["us-east-1"])
        )

    def _assert_failure(self, candidates, message):
        source = self._template(candidates)

        matches, transformed = self._transform(source)

        self.assertIsNone(transformed)
        self.assertEqual([match.rule.id for match in matches], ["E0001"])
        self.assertIn(message, matches[0].message)
        self.assertIn("Fn::ForEach::Values", source["Resources"])

    def test_gev_006_absent_account_find_in_map_collection_returns_e0001_without_transformed_template(
        self,
    ):
        """An absent requested value fails transformation without output."""
        self._assert_failure(
            {
                "111111111111": {"Names": ["one"]},
                "222222222222": {"Names": ["two"]},
            },
            "Can't resolve Fn::FindInMap",
        )

    def test_gev_006_empty_account_find_in_map_collection_returns_e0001_without_transformed_template(
        self,
    ):
        """An empty resolved list fails transformation without output."""
        self._assert_failure(
            {
                "111111111111": {"Values": []},
                "222222222222": {"Values": []},
            },
            "Fn::ForEach could not be resolved",
        )

    def test_gev_006_scalar_account_find_in_map_collection_returns_list_required_e0001(
        self,
    ):
        """A scalar collection reports the established list-required failure."""
        self._assert_failure(
            {
                "111111111111": {"Values": "one"},
                "222222222222": {"Values": "one"},
            },
            "Fn::ForEach collection must return a list",
        )

    def test_gev_006_object_account_find_in_map_collection_returns_list_required_e0001(
        self,
    ):
        """An object collection reports the established list-required failure."""
        self._assert_failure(
            {
                "111111111111": {"Values": {"Ref": "SharedValues"}},
                "222222222222": {"Values": {"Ref": "SharedValues"}},
            },
            "Fn::ForEach collection must return a list",
        )

    def test_gev_007_unsupported_member_stops_with_collection_value_e0001_without_partial_expansion(
        self,
    ):
        """An unsupported member stops expansion with no partial template."""
        self._assert_failure(
            {
                "111111111111": {"Values": ["supported", 1]},
                "222222222222": {"Values": ["supported", 1]},
            },
            "Fn::ForEach collection value must be",
        )

    def test_gev_007_supported_string_and_intrinsic_object_members_remain_eligible_for_loop_substitution(
        self,
    ):
        """Supported string and intrinsic-object members remain substitutable."""
        candidates = {
            "111111111111": {"Values": ["supported", {"Ref": "SharedValue"}]},
            "222222222222": {"Values": ["supported", {"Ref": "SharedValue"}]},
        }

        matches, transformed = self._transform(self._template(candidates))

        self.assertEqual(matches, [])
        self.assertIsNotNone(transformed)
        self.assertNotIn("Fn::ForEach::Values", transformed["Resources"])
        generated = [
            resource["Properties"]["DisplayName"]
            for name, resource in transformed["Resources"].items()
            if name != "Seed"
        ]
        self.assertEqual(len(generated), 2)
        self.assertIn("supported", generated)
        self.assertIn({"Ref": "SharedValue"}, generated)
