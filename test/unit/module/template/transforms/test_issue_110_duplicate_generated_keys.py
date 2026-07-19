"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from copy import deepcopy
from unittest import TestCase

from cfnlint.decode import convert_dict
from cfnlint.template import Template
from cfnlint.template.transforms._language_extensions import language_extension


class TestIssue110DuplicateGeneratedKeys(TestCase):
    fixture = "test/fixtures/templates/issues/issue_110_duplicate_generated_keys.yaml"

    def _account_collection(self, members):
        return {
            "Mappings": {
                "AccountMap": {
                    "111111111111": {"Members": members},
                    "222222222222": {"Members": members},
                }
            },
            "collection": {
                "Fn::FindInMap": [
                    "AccountMap",
                    {"Ref": "AWS::AccountId"},
                    "Members",
                ]
            },
        }

    def _assert_duplicate_failure(self, source, generated_key):
        original = deepcopy(source)

        matches, transformed = language_extension(
            Template(
                filename=self.fixture,
                template=source,
                regions=["us-east-1"],
            )
        )

        self.assertIsNone(transformed)
        self.assertEqual([match.rule.id for match in matches], ["E0001"])
        self.assertEqual(
            matches[0].message,
            (
                "Error transforming template: "
                f"Duplicate {generated_key} while doing transformation"
            ),
        )
        self.assertEqual(source, original)

    def test_gev_014_merging_account_collection_resource_key_collision_returns_duplicate_e0001_without_overwrite(
        self,
    ):
        """A generated Resource collision fails without replacing its existing value."""
        account_collection = self._account_collection(["Existing"])
        existing_resource = {
            "Type": "AWS::SNS::Topic",
            "Properties": {"DisplayName": "original-resource"},
        }
        source = convert_dict(
            {
                "Transform": "AWS::LanguageExtensions",
                "Mappings": account_collection["Mappings"],
                "Resources": {
                    "ExistingResource": existing_resource,
                    "Fn::ForEach::Resources": [
                        "Member",
                        account_collection["collection"],
                        {
                            "${Member}Resource": {
                                "Type": "AWS::SNS::Topic",
                                "Properties": {"DisplayName": "generated-resource"},
                            }
                        },
                    ],
                },
            }
        )

        self._assert_duplicate_failure(source, "ExistingResource")
        self.assertEqual(source["Resources"]["ExistingResource"], existing_resource)
        self.assertIn("Fn::ForEach::Resources", source["Resources"])

    def test_gev_014_merging_account_collection_output_key_collision_returns_duplicate_e0001_without_overwrite(
        self,
    ):
        """A generated Output collision fails without replacing its existing value."""
        account_collection = self._account_collection(["Existing"])
        existing_output = {"Value": "original-output"}
        source = convert_dict(
            {
                "Transform": "AWS::LanguageExtensions",
                "Mappings": account_collection["Mappings"],
                "Resources": {"Seed": {"Type": "AWS::SNS::Topic"}},
                "Outputs": {
                    "ExistingOutput": existing_output,
                    "Fn::ForEach::Outputs": [
                        "Member",
                        account_collection["collection"],
                        {"${Member}Output": {"Value": "generated-output"}},
                    ],
                },
            }
        )

        self._assert_duplicate_failure(source, "ExistingOutput")
        self.assertEqual(source["Outputs"]["ExistingOutput"], existing_output)
        self.assertIn("Fn::ForEach::Outputs", source["Outputs"])

    def test_gev_014_merging_second_sanitized_member_key_collision_returns_duplicate_e0001_without_partial_template(
        self,
    ):
        """A second sanitized-key collision fails without publishing partial output."""
        source = convert_dict(
            {
                "Transform": "AWS::LanguageExtensions",
                "Resources": {
                    "Seed": {"Type": "AWS::SNS::Topic"},
                    "Fn::ForEach::SanitizedMembers": [
                        "Member",
                        ["a-b", "ab"],
                        {
                            "Generated&{Member}": {
                                "Type": "AWS::SNS::Topic",
                                "Properties": {"DisplayName": {"Ref": "Member"}},
                            }
                        },
                    ],
                },
            }
        )

        self._assert_duplicate_failure(source, "Generatedab")
        self.assertNotIn("Generatedab", source["Resources"])
        self.assertIn("Fn::ForEach::SanitizedMembers", source["Resources"])
