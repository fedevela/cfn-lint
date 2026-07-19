"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0

Verification placeholders for the Fn::ForEach duplicate-key contract.
"""

import unittest

from cfnlint.decode import convert_dict
from cfnlint.template import Template
from cfnlint.template.transforms._language_extensions import language_extension


_PLACEHOLDER_REASON = (
    "Phase 05 verification placeholder; enable during Malkhut executable validation"
)


class TestForEachDuplicateKeyContract(unittest.TestCase):
    def _transform(self, template):
        return language_extension(
            Template(
                filename="foreach-duplicate-key-contract.yaml",
                template=convert_dict(
                    {"Transform": "AWS::LanguageExtensions", **template}
                ),
                regions=["us-east-1"],
            )
        )

    def _assert_duplicate_failure(self, template, duplicate_key):
        matches, transformed = self._transform(template)

        self.assertIsNone(transformed)
        self.assertEqual(["E0001"], [match.rule.id for match in matches])
        self.assertIn(
            f"Duplicate {duplicate_key} while doing transformation",
            matches[0].message,
        )

    @unittest.skip(_PLACEHOLDER_REASON)
    def test_foreach_013_distinct_iterations_generating_same_key_transform_reports_duplicate_failure(
        self,
    ):
        """GUID: FOREACH-013; a later generated key cannot overwrite an earlier one."""
        self._assert_duplicate_failure(
            {
                "Resources": {
                    "Fn::ForEach::DuplicateGenerated": [
                        "Identifier",
                        ["First", "Second"],
                        {"RepeatedResource": {"Type": "AWS::SQS::Queue"}},
                    ]
                }
            },
            "RepeatedResource",
        )

    @unittest.skip(_PLACEHOLDER_REASON)
    def test_foreach_013_generated_resource_matching_existing_sibling_transform_reports_duplicate_failure(
        self,
    ):
        """GUID: FOREACH-013; a generated resource cannot overwrite a sibling."""
        self._assert_duplicate_failure(
            {
                "Resources": {
                    "ExistingResource": {"Type": "AWS::S3::Bucket"},
                    "Fn::ForEach::ResourceCollision": [
                        "Identifier",
                        ["Existing"],
                        {
                            "${Identifier}Resource": {
                                "Type": "AWS::SQS::Queue"
                            }
                        },
                    ],
                }
            },
            "ExistingResource",
        )

    @unittest.skip(_PLACEHOLDER_REASON)
    def test_foreach_013_generated_output_matching_existing_sibling_transform_reports_duplicate_failure(
        self,
    ):
        """GUID: FOREACH-013; a generated output cannot overwrite a sibling."""
        self._assert_duplicate_failure(
            {
                "Resources": {"Bucket": {"Type": "AWS::S3::Bucket"}},
                "Outputs": {
                    "ExistingOutput": {"Value": "preserved"},
                    "Fn::ForEach::OutputCollision": [
                        "Identifier",
                        ["Existing"],
                        {"${Identifier}Output": {"Value": "replacement"}},
                    ],
                },
            },
            "ExistingOutput",
        )

    @unittest.skip(_PLACEHOLDER_REASON)
    def test_foreach_013_generated_nested_key_matching_existing_sibling_transform_reports_duplicate_failure(
        self,
    ):
        """GUID: FOREACH-013; a generated nested key cannot overwrite a sibling."""
        self._assert_duplicate_failure(
            {
                "Resources": {
                    "Bucket": {
                        "Type": "AWS::S3::Bucket",
                        "Metadata": {
                            "ExistingMetadata": "preserved",
                            "Fn::ForEach::NestedCollision": [
                                "Identifier",
                                ["Existing"],
                                {"${Identifier}Metadata": "replacement"},
                            ],
                        },
                    }
                }
            },
            "ExistingMetadata",
        )

    @unittest.skip(_PLACEHOLDER_REASON)
    def test_foreach_013_empty_loop_adjacent_to_existing_sibling_inserts_nothing_and_reports_no_duplicate(
        self,
    ):
        """GUID: FOREACH-013; an empty loop preserves its adjacent sibling."""
        matches, transformed = self._transform(
            {
                "Resources": {
                    "ExistingResource": {
                        "Type": "AWS::S3::Bucket",
                        "Metadata": {"Contract": "preserved"},
                    },
                    "Fn::ForEach::EmptyCollisionCandidate": [
                        "Identifier",
                        [],
                        {
                            "ExistingResource": {
                                "Type": "AWS::SQS::Queue"
                            }
                        },
                    ],
                }
            }
        )

        self.assertEqual([], matches)
        self.assertEqual(
            {
                "ExistingResource": {
                    "Type": "AWS::S3::Bucket",
                    "Metadata": {"Contract": "preserved"},
                }
            },
            transformed["Resources"],
        )

    @unittest.skip(_PLACEHOLDER_REASON)
    def test_foreach_013_unique_non_empty_loop_after_empty_loop_generates_all_entries_without_stale_state(
        self,
    ):
        """GUID: FOREACH-013; an empty loop leaves no stale duplicate state."""
        matches, transformed = self._transform(
            {
                "Resources": {
                    "ExistingResource": {"Type": "AWS::S3::Bucket"},
                    "Fn::ForEach::EmptyFirst": [
                        "Identifier",
                        [],
                        {
                            "Generated${Identifier}": {
                                "Type": "AWS::SNS::Topic"
                            }
                        },
                    ],
                    "Fn::ForEach::UniqueAfterEmpty": [
                        "Identifier",
                        ["First", "Second"],
                        {
                            "Generated${Identifier}": {
                                "Type": "AWS::SQS::Queue"
                            }
                        },
                    ],
                }
            }
        )

        self.assertEqual([], matches)
        self.assertEqual(
            {
                "ExistingResource": {"Type": "AWS::S3::Bucket"},
                "GeneratedFirst": {"Type": "AWS::SQS::Queue"},
                "GeneratedSecond": {"Type": "AWS::SQS::Queue"},
            },
            transformed["Resources"],
        )
