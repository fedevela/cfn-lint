"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0

Verification placeholders for the non-empty Fn::ForEach collection contract.
"""

import unittest

from cfnlint.decode import convert_dict
from cfnlint.template import Template
from cfnlint.template.transforms._language_extensions import language_extension


_PLACEHOLDER_REASON = (
    "Phase 05 verification placeholder; enable during Malkhut executable validation"
)


class TestForEachNonEmptyCollectionContract(unittest.TestCase):
    def _transform(self, template):
        cfn = Template(
            filename="non-empty-foreach.yaml",
            template=convert_dict(template),
            regions=["us-east-1"],
        )

        matches, transformed = language_extension(cfn)

        self.assertEqual([], matches)
        self.assertIsNotNone(transformed)
        return transformed

    @unittest.skip(_PLACEHOLDER_REASON)
    def test_foreach_007_008_non_empty_literal_resources_generate_one_substituted_fragment_per_value(
        self,
    ):
        """GUIDs: FOREACH-007, FOREACH-008; preserve literal expansion."""
        template = {
            "Transform": "AWS::LanguageExtensions",
            "Resources": {
                "Fn::ForEach::Queues": [
                    "Identifier",
                    ["Alpha", "Beta", "Gamma"],
                    {
                        "Queue${Identifier}": {
                            "Type": "AWS::SQS::Queue",
                            "Properties": {
                                "QueueName": {
                                    "Fn::Sub": "queue-${Identifier}"
                                }
                            },
                        }
                    },
                ]
            },
        }

        transformed = self._transform(template)

        self.assertEqual(
            {
                "QueueAlpha": {
                    "Type": "AWS::SQS::Queue",
                    "Properties": {"QueueName": "queue-Alpha"},
                },
                "QueueBeta": {
                    "Type": "AWS::SQS::Queue",
                    "Properties": {"QueueName": "queue-Beta"},
                },
                "QueueGamma": {
                    "Type": "AWS::SQS::Queue",
                    "Properties": {"QueueName": "queue-Gamma"},
                },
            },
            transformed["Resources"],
        )

    @unittest.skip(_PLACEHOLDER_REASON)
    def test_foreach_007_008_non_empty_find_in_map_outputs_generate_every_substituted_fragment(
        self,
    ):
        """GUIDs: FOREACH-007, FOREACH-008; preserve mapped expansion."""
        template = {
            "Transform": "AWS::LanguageExtensions",
            "Mappings": {
                "LoopValues": {
                    "NonEmpty": {"Names": ["First", "Second", "Third"]}
                }
            },
            "Resources": {"ExistingBucket": {"Type": "AWS::S3::Bucket"}},
            "Outputs": {
                "Fn::ForEach::Names": [
                    "Identifier",
                    {"Fn::FindInMap": ["LoopValues", "NonEmpty", "Names"]},
                    {
                        "Output${Identifier}": {
                            "Value": {"Ref": "Identifier"}
                        }
                    },
                ]
            },
        }

        transformed = self._transform(template)

        self.assertEqual(
            {
                "OutputFirst": {"Value": "First"},
                "OutputSecond": {"Value": "Second"},
                "OutputThird": {"Value": "Third"},
            },
            transformed["Outputs"],
        )

    @unittest.skip(_PLACEHOLDER_REASON)
    def test_foreach_008_ampersand_form_sanitizes_non_alphanumeric_values_in_keys_and_values(
        self,
    ):
        """GUID: FOREACH-008; preserve established &{Identifier} sanitizing."""
        template = {
            "Transform": "AWS::LanguageExtensions",
            "Resources": {
                "Fn::ForEach::SanitizedBuckets": [
                    "Identifier",
                    ["alpha-beta", "gamma.delta", "epsilon/zeta"],
                    {
                        "Bucket&{Identifier}": {
                            "Type": "AWS::S3::Bucket",
                            "Properties": {
                                "BucketName": {
                                    "Fn::Sub": "bucket-&{Identifier}"
                                }
                            },
                        }
                    },
                ]
            },
        }

        transformed = self._transform(template)

        self.assertEqual(
            {
                "Bucketalphabeta": {
                    "Type": "AWS::S3::Bucket",
                    "Properties": {"BucketName": "bucket-alphabeta"},
                },
                "Bucketgammadelta": {
                    "Type": "AWS::S3::Bucket",
                    "Properties": {"BucketName": "bucket-gammadelta"},
                },
                "Bucketepsilonzeta": {
                    "Type": "AWS::S3::Bucket",
                    "Properties": {"BucketName": "bucket-epsilonzeta"},
                },
            },
            transformed["Resources"],
        )

    @unittest.skip(_PLACEHOLDER_REASON)
    def test_foreach_007_008_supported_nested_non_empty_loops_preserve_cross_product_and_substitution(
        self,
    ):
        """GUIDs: FOREACH-007, FOREACH-008; preserve nested loop behavior."""
        template = {
            "Transform": "AWS::LanguageExtensions",
            "Mappings": {
                "LoopValues": {
                    "NonEmpty": {"Names": ["one-value", "two.value"]}
                }
            },
            "Resources": {"ExistingBucket": {"Type": "AWS::S3::Bucket"}},
            "Outputs": {
                "Fn::ForEach::Outer": [
                    "Outer",
                    ["A", "B"],
                    {
                        "Fn::ForEach::Inner": [
                            "Inner",
                            {
                                "Fn::FindInMap": [
                                    "LoopValues",
                                    "NonEmpty",
                                    "Names",
                                ]
                            },
                            {
                                "Result${Outer}&{Inner}": {
                                    "Value": {
                                        "Fn::Sub": "${Outer}-&{Inner}"
                                    }
                                }
                            },
                        ]
                    },
                ]
            },
        }

        transformed = self._transform(template)

        self.assertEqual(
            {
                "ResultAonevalue": {"Value": "A-onevalue"},
                "ResultAtwovalue": {"Value": "A-twovalue"},
                "ResultBonevalue": {"Value": "B-onevalue"},
                "ResultBtwovalue": {"Value": "B-twovalue"},
            },
            transformed["Outputs"],
        )
