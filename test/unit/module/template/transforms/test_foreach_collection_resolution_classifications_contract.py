"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0

Verification coverage for Fn::ForEach collection resolution classifications.
"""

import unittest
from unittest import mock

from cfnlint.decode import convert_dict
from cfnlint.template import Template
from cfnlint.template.transforms._language_extensions import (
    _ForEachCollection,
    language_extension,
)


class TestForEachCollectionResolutionClassificationsContract(unittest.TestCase):
    def _template(self, template=None):
        return Template(
            filename="foreach-collection-resolution-classifications.yaml",
            template=convert_dict(template or {}),
            regions=["us-east-1"],
        )

    def _loop_template(self, collection, mappings=None):
        template = {
            "Transform": "AWS::LanguageExtensions",
            "Resources": {
                "Fn::ForEach::ClassifiedValues": [
                    "Identifier",
                    collection,
                    {
                        "Queue${Identifier}": {
                            "Type": "AWS::SQS::Queue"
                        }
                    },
                ]
            },
        }
        if mappings is not None:
            template["Mappings"] = mappings
        return self._template(template)

    def test_foreach_009_non_list_or_unsupported_intrinsic_collection_transform_reports_established_type_diagnostic(
        self,
    ):
        """GUID: FOREACH-009; unsupported collection sources remain invalid."""
        cases = (
            (None, "Collection must be a list or an object"),
            ("not-a-list", "Collection must be a list or an object"),
            (0, "Collection must be a list or an object"),
            (False, "Collection must be a list or an object"),
            ({"Fn::Sub": "${Unsupported}"}, "Unsupported value"),
        )

        for collection, diagnostic in cases:
            with self.subTest(collection=collection):
                matches, transformed = language_extension(
                    self._loop_template(collection)
                )

                self.assertIsNone(transformed)
                self.assertEqual(["E0001"], [match.rule.id for match in matches])
                self.assertIn(diagnostic, matches[0].message)

    def test_foreach_009_supported_intrinsic_resolving_to_falsy_non_list_is_rejected_not_zero_iteration(
        self,
    ):
        """GUID: FOREACH-009; None, '', 0, and False are not empty lists."""
        for value in (None, "", 0, False):
            with self.subTest(value=value):
                matches, transformed = language_extension(
                    self._loop_template(
                        {
                            "Fn::FindInMap": [
                                "CollectionMap",
                                "Case",
                                "Values",
                            ]
                        },
                        {
                            "CollectionMap": {
                                "Case": {"Values": value}
                            }
                        },
                    )
                )

                self.assertIsNone(transformed)
                self.assertEqual(["E0001"], [match.rule.id for match in matches])
                self.assertIn(
                    "Fn::ForEach collection must return a list",
                    matches[0].message,
                )

    def test_foreach_012_resolved_non_empty_collection_with_invalid_member_returns_established_transform_failure(
        self,
    ):
        """GUID: FOREACH-012; an invalid resolved member prevents publication."""
        template = {
            "Transform": "AWS::LanguageExtensions",
            "Mappings": {
                "CollectionMap": {"Case": {"Values": ["Valid", 42]}}
            },
            "Resources": {
                "Fn::ForEach::MappedValues": [
                    "Identifier",
                    {"Fn::FindInMap": ["CollectionMap", "Case", "Values"]},
                    {
                        "Queue${Identifier}": {
                            "Type": "AWS::SQS::Queue"
                        }
                    },
                ]
            },
        }

        matches, transformed = language_extension(self._template(template))

        self.assertIsNone(transformed)
        self.assertEqual(["E0001"], [match.rule.id for match in matches])
        self.assertIn("Fn::ForEach collection value must be", matches[0].message)

    def test_foreach_014_unresolved_supported_intrinsic_generates_established_approximation_entries_not_zero_iterations(
        self,
    ):
        """GUID: FOREACH-014; resolver failure retains approximation entries."""
        collection = {
            "Fn::FindInMap": ["MissingMap", "MissingCase", "MissingValues"]
        }

        with mock.patch(
            "cfnlint.template.transforms._language_extensions.random.choices",
            side_effect=[list("AAAAAAA"), list("BBBBBBB")],
        ):
            matches, transformed = language_extension(
                self._loop_template(collection)
            )

        self.assertEqual([], matches)
        self.assertEqual(
            {
                "QueueAAAAAAA": {"Type": "AWS::SQS::Queue"},
                "QueueBBBBBBB": {"Type": "AWS::SQS::Queue"},
            },
            transformed["Resources"],
        )

    def test_foreach_009_014_empty_known_and_unresolved_collections_remain_observably_distinct(
        self,
    ):
        """GUIDs: FOREACH-009, FOREACH-014; preserve all three classifications."""
        cfn = self._template()
        empty = _ForEachCollection([])
        known = _ForEachCollection(["KnownValue"])
        unresolved = _ForEachCollection(
            {"Fn::FindInMap": ["MissingMap", "MissingCase", "MissingValues"]}
        )

        with mock.patch(
            "cfnlint.template.transforms._language_extensions.random.choices",
            side_effect=[list("AAAAAAA"), list("BBBBBBB")],
        ):
            empty_values = list(empty.values(cfn, {}))
            known_values = list(known.values(cfn, {}))
            unresolved_values = list(unresolved.values(cfn, {}))

        self.assertEqual([], empty_values)
        self.assertEqual(["KnownValue"], known_values)
        self.assertEqual(["AAAAAAA", "BBBBBBB"], unresolved_values)
