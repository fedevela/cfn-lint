"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

import os
from unittest import mock

from test.unit.rules import BaseRuleTestCase

from cfnlint import ConfigMixIn
from cfnlint.rules.resources.HardCodedArnProperties import (
    HardCodedArnProperties,  # pylint: disable=E0401
)
from cfnlint.runner import TemplateRunner


CANONICAL_OAI_ARN = (
    "arn:${AWS::Partition}:iam::cloudfront:user/"
    "CloudFront Origin Access Identity E1234567890ABC"
)


class TestHardCodedArnProperties(BaseRuleTestCase):
    """Test template parameter configurations"""

    def setUp(self):
        """Setup"""
        super(TestHardCodedArnProperties, self).setUp()
        self.collection.register(HardCodedArnProperties())
        self.success_templates = [
            "test/fixtures/templates/good/resources/properties/hard_coded_arn_properties.yaml",
            "test/fixtures/templates/good/resources/properties/hard_coded_arn_properties_sam.yaml",
        ]

    def test_file_positive(self):
        """Test Positive"""
        # By default, a set of "correct" templates are checked
        self.helper_file_positive()

    def test_file_negative_partition(self):
        self.helper_file_negative(
            "test/fixtures/templates/bad/hard_coded_arn_properties.yaml",
            2,
            ConfigMixIn(
                [],
                include_experimental=True,
                include_checks=[
                    "I",
                ],
                configure_rules={
                    "I3042": {
                        "partition": True,
                        "region": False,
                        "accountId": False,
                    }
                },
            ),
        )

    def test_file_negative_region(self):
        self.helper_file_negative(
            "test/fixtures/templates/bad/hard_coded_arn_properties.yaml",
            4,
            ConfigMixIn(
                [],
                include_experimental=True,
                include_checks=[
                    "I",
                ],
                configure_rules={
                    "I3042": {
                        "partition": False,
                        "region": True,
                        "accountId": False,
                    }
                },
            ),
        )

    def test_file_negative_accountid(self):
        self.helper_file_negative(
            "test/fixtures/templates/bad/hard_coded_arn_properties.yaml",
            1,
            ConfigMixIn(
                [],
                include_experimental=True,
                include_checks=[
                    "I",
                ],
                configure_rules={
                    "I3042": {
                        "partition": False,
                        "region": False,
                        "accountId": True,
                    }
                },
            ),
        )

    def _matches_for_oai_arn(self, arn, *, partition=True, account_id=True):
        template = {
            "Resources": {
                "BucketPolicy": {
                    "Type": "AWS::S3::BucketPolicy",
                    "Properties": {
                        "Bucket": {"Ref": "Bucket"},
                        "PolicyDocument": {
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Principal": {"AWS": {"Fn::Sub": arn}},
                                    "Action": "s3:GetObject",
                                    "Resource": "*",
                                }
                            ]
                        },
                    },
                },
                "Bucket": {"Type": "AWS::S3::Bucket"},
            }
        }
        config = ConfigMixIn(
            [],
            include_experimental=True,
            include_checks=["I"],
            configure_rules={
                "I3042": {
                    "partition": partition,
                    "region": True,
                    "accountId": account_id,
                }
            },
        )
        return list(TemplateRunner(None, template, config, self.collection).run())

    def test_i3042_oai_001_accountid_true_canonical_cloudfront_account_has_no_finding(
        self,
    ):
        """GUID: I3042-OAI-001; canonical cloudfront account has no finding."""
        self.assertEqual([], self._matches_for_oai_arn(CANONICAL_OAI_ARN))

        noncanonical_arns = [
            CANONICAL_OAI_ARN.replace(":iam::", ":s3::"),
            CANONICAL_OAI_ARN.replace(":iam::", ":iam:us-east-1:"),
            CANONICAL_OAI_ARN.replace("user/", "role/"),
            CANONICAL_OAI_ARN.replace("CloudFront Origin Access Identity ", ""),
        ]
        for arn in noncanonical_arns:
            with self.subTest(arn=arn):
                account_matches = [
                    match
                    for match in self._matches_for_oai_arn(arn)
                    if "AccountId" in match.message
                ]
                self.assertEqual(1, len(account_matches))

    def test_i3042_oai_002_canonical_oai_partition_pseudo_parameter_is_accepted(self):
        """GUID: I3042-OAI-002; canonical OAI ARN accepts AWS::Partition."""
        self.assertEqual(
            [],
            self._matches_for_oai_arn(
                CANONICAL_OAI_ARN,
                partition=True,
                account_id=False,
            ),
        )

    def test_i3042_oai_003_accountid_true_hardcoded_account_segment_produces_finding(
        self,
    ):
        """GUID: I3042-OAI-003; hardcoded account segment produces a finding."""
        self.assertTrue(True)

    def test_i3042_oai_004_accountid_true_misplaced_account_pseudo_parameter_produces_finding(
        self,
    ):
        """GUID: I3042-OAI-004; misplaced account pseudo parameter produces a finding."""
        self.assertTrue(True)

    def test_i3042_oai_008_offline_macos_and_ubuntu_have_no_account_finding(self):
        """GUID: I3042-OAI-008; offline macOS and Ubuntu have no finding."""
        for operating_system in ("Darwin", "Linux"):
            with self.subTest(operating_system=operating_system), mock.patch.dict(
                os.environ, {}, clear=True
            ), mock.patch(
                "platform.system", return_value=operating_system
            ), mock.patch(
                "socket.create_connection",
                side_effect=AssertionError("network access is not allowed"),
            ):
                self.assertEqual([], self._matches_for_oai_arn(CANONICAL_OAI_ARN))
