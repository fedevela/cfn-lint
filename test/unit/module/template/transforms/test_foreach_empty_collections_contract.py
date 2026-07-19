"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0

Verification coverage for the empty Fn::ForEach collection contract.
"""

import unittest
from copy import deepcopy

from cfnlint.decode import convert_dict
from cfnlint.template import Template
from cfnlint.template.transforms._language_extensions import (
    _ForEachCollection,
    language_extension,
)


class TestForEachEmptyCollectionContract(unittest.TestCase):
    def _template(self, template):
        return Template(
            filename="empty-foreach.yaml",
            template=convert_dict(template),
            regions=["us-east-1"],
        )

    def _transform(self, template):
        matches, transformed = language_extension(self._template(template))
        self.assertEqual([], matches)
        self.assertIsNotNone(transformed)
        return transformed

    def test_foreach_001_literal_empty_collection_iterates_zero_times(self):
        """GUID: FOREACH-001; a literal [] is a valid collection boundary."""
        collection = _ForEachCollection([])

        self.assertEqual([], list(collection.values(self._template({}), {})))

    def test_foreach_002_find_in_map_empty_collection_iterates_zero_times(self):
        """GUID: FOREACH-002; a resolved Fn::FindInMap [] is valid."""
        cfn = self._template(
            {"Mappings": {"LoopValues": {"Empty": {"Names": []}}}}
        )
        collection = _ForEachCollection(
            {"Fn::FindInMap": ["LoopValues", "Empty", "Names"]}
        )

        self.assertEqual([], list(collection.values(cfn, {})))

    def test_foreach_001_003_004_005_literal_empty_resources_loop_is_removed(self):
        """GUIDs: FOREACH-001, FOREACH-003, FOREACH-004, FOREACH-005."""
        sibling_resource = {
            "Type": "AWS::S3::Bucket",
            "Metadata": {"Contract": "unchanged"},
        }
        sibling_output = {"Value": "unchanged"}
        template = {
            "Transform": "AWS::LanguageExtensions",
            "Resources": {
                "SiblingBucket": deepcopy(sibling_resource),
                "Fn::ForEach::EmptyResources": [
                    "Identifier",
                    [],
                    {
                        "Generated${Identifier}": {
                            "Type": "AWS::SQS::Queue"
                        }
                    },
                ],
            },
            "Outputs": {"SiblingOutput": deepcopy(sibling_output)},
        }

        transformed = self._transform(template)

        self.assertEqual({"SiblingBucket": sibling_resource}, transformed["Resources"])
        self.assertEqual({"SiblingOutput": sibling_output}, transformed["Outputs"])
        self.assertNotIn("Fn::ForEach::EmptyResources", transformed["Resources"])

    def test_foreach_002_003_004_005_find_in_map_empty_outputs_loop_is_removed(self):
        """GUIDs: FOREACH-002, FOREACH-003, FOREACH-004, FOREACH-005."""
        mappings = {"LoopValues": {"Empty": {"Names": []}}}
        sibling_resource = {"Type": "AWS::S3::Bucket"}
        sibling_output = {"Value": {"Ref": "SiblingBucket"}}
        template = {
            "Transform": "AWS::LanguageExtensions",
            "Mappings": deepcopy(mappings),
            "Resources": {"SiblingBucket": deepcopy(sibling_resource)},
            "Outputs": {
                "SiblingOutput": deepcopy(sibling_output),
                "Fn::ForEach::EmptyOutputs": [
                    "Identifier",
                    {"Fn::FindInMap": ["LoopValues", "Empty", "Names"]},
                    {"Generated${Identifier}": {"Value": {"Ref": "Identifier"}}},
                ],
            },
        }

        transformed = self._transform(template)

        self.assertEqual(mappings, transformed["Mappings"])
        self.assertEqual({"SiblingBucket": sibling_resource}, transformed["Resources"])
        self.assertEqual({"SiblingOutput": sibling_output}, transformed["Outputs"])
        self.assertNotIn("Fn::ForEach::EmptyOutputs", transformed["Outputs"])

    def test_foreach_006_literal_empty_nested_loop_preserves_outer_expansion(self):
        """GUID: FOREACH-006; nested literal [] does not stop valid expansion."""
        template = {
            "Transform": "AWS::LanguageExtensions",
            "Resources": {"SiblingBucket": {"Type": "AWS::S3::Bucket"}},
            "Outputs": {
                "SiblingOutput": {"Value": "unchanged"},
                "Fn::ForEach::Outer": [
                    "Outer",
                    ["A", "B"],
                    {
                        "Expanded${Outer}": {"Value": {"Ref": "Outer"}},
                        "Fn::ForEach::EmptyNested": [
                            "Inner",
                            [],
                            {
                                "Nested${Outer}${Inner}": {
                                    "Value": {"Ref": "Inner"}
                                }
                            },
                        ],
                    },
                ],
            },
        }

        transformed = self._transform(template)

        self.assertEqual(
            {
                "SiblingOutput": {"Value": "unchanged"},
                "ExpandedA": {"Value": "A"},
                "ExpandedB": {"Value": "B"},
            },
            transformed["Outputs"],
        )

    def test_foreach_006_find_in_map_empty_nested_loop_preserves_outer_expansion(self):
        """GUID: FOREACH-006; nested resolved [] does not stop valid expansion."""
        template = {
            "Transform": "AWS::LanguageExtensions",
            "Mappings": {"LoopValues": {"Empty": {"Names": []}}},
            "Resources": {
                "SiblingBucket": {"Type": "AWS::S3::Bucket"},
                "Fn::ForEach::Outer": [
                    "Outer",
                    ["A", "B"],
                    {
                        "Expanded${Outer}": {"Type": "AWS::SQS::Queue"},
                        "Fn::ForEach::EmptyNested": [
                            "Inner",
                            {
                                "Fn::FindInMap": [
                                    "LoopValues",
                                    "Empty",
                                    "Names",
                                ]
                            },
                            {
                                "Nested${Outer}${Inner}": {
                                    "Type": "AWS::SNS::Topic"
                                }
                            },
                        ],
                    },
                ],
            },
            "Outputs": {"SiblingOutput": {"Value": "unchanged"}},
        }

        transformed = self._transform(template)

        self.assertEqual(
            {
                "SiblingBucket": {"Type": "AWS::S3::Bucket"},
                "ExpandedA": {"Type": "AWS::SQS::Queue"},
                "ExpandedB": {"Type": "AWS::SQS::Queue"},
            },
            transformed["Resources"],
        )
        self.assertEqual(
            {"SiblingOutput": {"Value": "unchanged"}}, transformed["Outputs"]
        )
