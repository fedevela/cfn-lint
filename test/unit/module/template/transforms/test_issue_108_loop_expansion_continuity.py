"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from unittest import TestCase

from cfnlint.decode import convert_dict
from cfnlint.template import Template
from cfnlint.template.transforms._language_extensions import language_extension


class TestIssue108LoopExpansionContinuity(TestCase):
    fixture = "test/fixtures/templates/issues/issue_108_loop_continuity.yaml"

    def _transform(self, template):
        return language_extension(
            Template(filename=self.fixture, template=template, regions=["us-east-1"])
        )

    def _account_collection(self):
        return {
            "Fn::FindInMap": [
                "AccountMap",
                {"Ref": "AWS::AccountId"},
                "Members",
            ]
        }

    def _template(self, resources, outputs=None, parameters=None):
        template = {
            "Transform": "AWS::LanguageExtensions",
            "Mappings": {
                "AccountMap": {
                    "111111111111": {"Members": ["Zulu", "Alpha"]},
                    "222222222222": {"Members": ["Zulu", "Alpha"]},
                }
            },
            "Resources": resources,
        }
        if outputs is not None:
            template["Outputs"] = outputs
        if parameters is not None:
            template["Parameters"] = parameters
        return convert_dict(template)

    def _assert_no_foreach(self, value):
        if isinstance(value, dict):
            for key, child in value.items():
                self.assertFalse(
                    isinstance(key, str) and key.startswith("Fn::ForEach::"),
                    key,
                )
                self._assert_no_foreach(child)
        elif isinstance(value, list):
            for child in value:
                self._assert_no_foreach(child)

    def test_gev_009_account_collection_expands_in_resources_outputs_and_inner_nested_loop_without_foreach(
        self,
    ):
        """Equivalent account collections expand at every supported loop locus."""
        source = self._template(
            {
                "Fn::ForEach::Resources": [
                    "Member",
                    self._account_collection(),
                    {
                        "Resource${Member}": {
                            "Type": "AWS::SNS::Topic",
                            "Properties": {"DisplayName": {"Ref": "Member"}},
                        }
                    },
                ],
                "Fn::ForEach::Outer": [
                    "Group",
                    ["Nested"],
                    {
                        "Fn::ForEach::Inner": [
                            "Member",
                            self._account_collection(),
                            {
                                "${Group}${Member}": {
                                    "Type": "AWS::SNS::Topic",
                                    "Properties": {
                                        "DisplayName": {
                                            "Fn::Sub": "${Group}-${Member}"
                                        }
                                    },
                                }
                            },
                        ]
                    },
                ],
            },
            {
                "Fn::ForEach::Outputs": [
                    "Member",
                    self._account_collection(),
                    {
                        "Output${Member}": {
                            "Value": {"Fn::Sub": "output-${Member}"}
                        }
                    },
                ]
            },
        )

        matches, transformed = self._transform(source)

        self.assertEqual(matches, [])
        self.assertEqual(
            list(transformed["Resources"]),
            ["ResourceZulu", "ResourceAlpha", "NestedZulu", "NestedAlpha"],
        )
        self.assertEqual(
            transformed["Resources"]["NestedAlpha"]["Properties"]["DisplayName"],
            "Nested-Alpha",
        )
        self.assertEqual(list(transformed["Outputs"]), ["OutputZulu", "OutputAlpha"])
        self.assertEqual(
            transformed["Outputs"]["OutputZulu"], {"Value": "output-Zulu"}
        )
        self._assert_no_foreach(transformed)

    def test_gev_010_literal_list_collection_preserves_member_count_keys_substitutions_and_intrinsics(
        self,
    ):
        """Literal-list expansion retains every established observable result."""
        source = self._template(
            {
                "Fn::ForEach::LiteralMembers": [
                    "Member",
                    ["One", "Two"],
                    {
                        "Literal${Member}": {
                            "Type": "AWS::SNS::Topic",
                            "Properties": {
                                "DisplayName": {"Ref": "Member"},
                                "TopicName": {"Ref": "SharedTopicName"},
                            },
                        }
                    },
                ]
            }
        )

        matches, transformed = self._transform(source)

        self.assertEqual(matches, [])
        self.assertEqual(list(transformed["Resources"]), ["LiteralOne", "LiteralTwo"])
        self.assertEqual(
            transformed["Resources"]["LiteralOne"]["Properties"],
            {"DisplayName": "One", "TopicName": {"Ref": "SharedTopicName"}},
        )
        self.assertEqual(
            transformed["Resources"]["LiteralTwo"]["Properties"],
            {"DisplayName": "Two", "TopicName": {"Ref": "SharedTopicName"}},
        )
        self._assert_no_foreach(transformed)

    def test_gev_010_list_parameter_collection_preserves_member_count_keys_substitutions_and_intrinsics(
        self,
    ):
        """List-parameter expansion retains every established observable result."""
        source = self._template(
            {
                "Fn::ForEach::ParameterMembers": [
                    "Member",
                    {"Ref": "Members"},
                    {
                        "Parameter&{Member}": {
                            "Type": "AWS::SNS::Topic",
                            "Properties": {"DisplayName": {"Ref": "Member"}},
                        }
                    },
                ]
            },
            parameters={"Members": {"Type": "CommaDelimitedList"}},
        )

        matches, transformed = self._transform(source)

        self.assertEqual(matches, [])
        self.assertEqual(
            list(transformed["Resources"]), ["Parameter03b8", "Parameter03ed"]
        )
        self.assertEqual(
            transformed["Resources"]["Parameter03b8"]["Properties"]["DisplayName"],
            {"Fn::Select": [0, {"Ref": "Members"}]},
        )
        self.assertEqual(
            transformed["Resources"]["Parameter03ed"]["Properties"]["DisplayName"],
            {"Fn::Select": [1, {"Ref": "Members"}]},
        )
        self._assert_no_foreach(transformed)

    def test_gev_011_account_id_ref_in_generated_output_remains_pseudo_parameter(
        self,
    ):
        """A generated output retains Ref AWS::AccountId without inference."""
        source = self._template(
            {"Seed": {"Type": "AWS::SNS::Topic"}},
            {
                "Fn::ForEach::Accounts": [
                    "Member",
                    ["Current"],
                    {
                        "Account${Member}": {
                            "Value": {"Ref": "AWS::AccountId"}
                        }
                    },
                ]
            },
        )

        matches, transformed = self._transform(source)

        self.assertEqual(matches, [])
        self.assertEqual(
            transformed["Outputs"],
            {"AccountCurrent": {"Value": {"Ref": "AWS::AccountId"}}},
        )
        self._assert_no_foreach(transformed)

    def test_gev_018_repeated_and_nested_account_collection_resolutions_preserve_order_and_expansion(
        self,
    ):
        """Every invocation receives the same ordered account collection."""
        source = self._template(
            {
                "Fn::ForEach::First": [
                    "Member",
                    self._account_collection(),
                    {"First${Member}": {"Type": "AWS::SNS::Topic"}},
                ],
                "Fn::ForEach::Second": [
                    "Member",
                    self._account_collection(),
                    {"Second${Member}": {"Type": "AWS::SNS::Topic"}},
                ],
                "Fn::ForEach::Outer": [
                    "Prefix",
                    ["Nested"],
                    {
                        "Fn::ForEach::Inner": [
                            "Member",
                            self._account_collection(),
                            {
                                "${Prefix}${Member}": {
                                    "Type": "AWS::SNS::Topic"
                                }
                            },
                        ]
                    },
                ],
            }
        )

        matches, transformed = self._transform(source)

        self.assertEqual(matches, [])
        self.assertEqual(
            list(transformed["Resources"]),
            [
                "FirstZulu",
                "FirstAlpha",
                "SecondZulu",
                "SecondAlpha",
                "NestedZulu",
                "NestedAlpha",
            ],
        )
        self._assert_no_foreach(transformed)
