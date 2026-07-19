"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from contextlib import nullcontext
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from cfnlint.decode import convert_dict
from cfnlint.template import Template
from cfnlint.template.transforms._language_extensions import (
    _ForEachValueFnFindInMap,
    language_extension,
)


class TestIssue109MalformedIntrinsicDiagnostics(TestCase):
    fixture = "test/fixtures/templates/issues/issue_109_malformed_intrinsics.yaml"

    def _template(self, foreach_value):
        return convert_dict(
            {
                "Transform": "AWS::LanguageExtensions",
                "Mappings": {
                    "AccountMap": {
                        "111111111111": {"Values": ["One"]},
                        "222222222222": {"Values": ["One"]},
                    }
                },
                "Resources": {
                    "Seed": {"Type": "AWS::SNS::Topic"},
                    "Fn::ForEach::Values": foreach_value,
                },
            }
        )

    def _assert_failure(self, foreach_value, message, before_account_inference=False):
        source = self._template(foreach_value)
        original = deepcopy(source)
        cfn = Template(
            filename=self.fixture,
            template=source,
            regions=["us-east-1"],
        )

        if before_account_inference:
            inference = patch.object(
                _ForEachValueFnFindInMap,
                "_uses_runtime_account",
                side_effect=AssertionError(
                    "account inference must not inspect a malformed Fn::FindInMap"
                ),
            )
        else:
            inference = nullcontext(None)

        with inference as account_inference:
            matches, transformed = language_extension(cfn)

        self.assertIsNone(transformed)
        self.assertEqual([match.rule.id for match in matches], ["E0001"])
        self.assertEqual(matches[0].message, f"Error transforming template: {message}")
        self.assertEqual(source, original)
        self.assertIn("Fn::ForEach::Values", source["Resources"])
        if before_account_inference:
            self.assertIsNotNone(account_inference)
            account_inference.assert_not_called()

    def test_gev_012_non_list_foreach_value_returns_structural_e0001_without_transformed_template(
        self,
    ):
        """A non-list declaration retains the three-element-list diagnostic."""
        self._assert_failure(
            {"Identifier": "Value"},
            "Fn::ForEach values must be a list of 3 elements",
        )

    def test_gev_012_wrong_arity_foreach_list_returns_structural_e0001_without_transformed_template(
        self,
    ):
        """Lists below and above three elements retain the structural diagnostic."""
        for value in ([], ["Value", []], ["Value", [], {}, "extra"]):
            with self.subTest(operand_count=len(value)):
                self._assert_failure(
                    value,
                    "Fn::ForEach values must be a list of 3 elements",
                )

    def test_gev_012_unsupported_foreach_identifier_returns_established_e0001_without_transformed_template(
        self,
    ):
        """An unsupported identifier stops transformation with no output."""
        self._assert_failure(
            [["Value"], ["One"], {"Result${Value}": {"Type": "AWS::SNS::Topic"}}],
            "Unsupported value ['Value']",
        )

    def test_gev_012_scalar_foreach_collection_returns_list_or_object_e0001_without_transformed_template(
        self,
    ):
        """A scalar collection retains the list-or-object diagnostic."""
        self._assert_failure(
            ["Value", "One", {"Result${Value}": {"Type": "AWS::SNS::Topic"}}],
            "Collection must be a list or an object",
        )

    def test_gev_012_unsupported_intrinsic_foreach_collection_returns_established_e0001_without_transformed_template(
        self,
    ):
        """An unsupported intrinsic collection stops before account inference."""
        self._assert_failure(
            [
                "Value",
                {"Fn::Sub": "${Values}"},
                {"Result${Value}": {"Type": "AWS::SNS::Topic"}},
            ],
            "Unsupported value {'Fn::Sub': '${Values}'}",
        )

    def test_gev_012_non_object_foreach_output_returns_dict_required_e0001_without_transformed_template(
        self,
    ):
        """A non-object loop output retains the object-required diagnostic."""
        self._assert_failure(
            ["Value", ["One"], ["Result${Value}"]],
            "Output must be a dict",
        )

    def test_gev_013_non_list_find_in_map_returns_list_required_e0001_before_account_inference(
        self,
    ):
        """A non-list FindInMap is rejected before account inference."""
        self._assert_failure(
            [
                "Value",
                {"Fn::FindInMap": "AccountMap"},
                {"Result${Value}": {"Type": "AWS::SNS::Topic"}},
            ],
            "Fn::FindInMap should be a list",
            before_account_inference=True,
        )

    def test_gev_013_unsupported_find_in_map_operand_count_returns_arity_e0001_before_account_inference(
        self,
    ):
        """FindInMap operand counts around the supported range retain its diagnostic."""
        for operands in (
            ["AccountMap", {"Ref": "AWS::AccountId"}],
            ["AccountMap", {"Ref": "AWS::AccountId"}, "Values", {}, "extra"],
        ):
            with self.subTest(operand_count=len(operands)):
                self._assert_failure(
                    [
                        "Value",
                        {"Fn::FindInMap": operands},
                        {"Result${Value}": {"Type": "AWS::SNS::Topic"}},
                    ],
                    "Fn::FindInMap requires a list of 3 or 4 values",
                    before_account_inference=True,
                )

    def test_gev_013_non_object_find_in_map_option_returns_default_value_object_e0001_before_account_inference(
        self,
    ):
        """A non-object fourth operand retains the DefaultValue-object diagnostic."""
        self._assert_failure(
            [
                "Value",
                {
                    "Fn::FindInMap": [
                        "AccountMap",
                        {"Ref": "AWS::AccountId"},
                        "Values",
                        "fallback",
                    ]
                },
                {"Result${Value}": {"Type": "AWS::SNS::Topic"}},
            ],
            "Fn::FindInMap parameter must be an object with key 'DefaultValue'",
            before_account_inference=True,
        )

    def test_gev_013_option_without_only_default_value_returns_malformed_default_value_e0001_before_account_inference(
        self,
    ):
        """A fourth-operand object must contain exactly the DefaultValue key."""
        for option in (
            {},
            {"Default": "fallback"},
            {"DefaultValue": "fallback", "Extra": "value"},
        ):
            with self.subTest(option=option):
                self._assert_failure(
                    [
                        "Value",
                        {
                            "Fn::FindInMap": [
                                "AccountMap",
                                {"Ref": "AWS::AccountId"},
                                "Values",
                                option,
                            ]
                        },
                        {"Result${Value}": {"Type": "AWS::SNS::Topic"}},
                    ],
                    "Fn::FindInMap parameter only supports 'DefaultValue'",
                    before_account_inference=True,
                )
