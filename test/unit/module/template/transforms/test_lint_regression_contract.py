"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from cfnlint import lint
from cfnlint.decode import cfn_yaml
from cfnlint.template import Template
from cfnlint.template.transforms._language_extensions import language_extension


REPRODUCTION_TEMPLATE = """\
AWSTemplateFormatVersion: 2010-09-09
Transform: AWS::LanguageExtensions
Mappings:
  AccountEmails:
    123456789012:
      Emails:
        - test@test.com
Resources:
  Topic:
    Type: AWS::SNS::Topic
  Fn::ForEach::Subscriptions:
    - Email
    - Fn::FindInMap:
        - AccountEmails
        - Ref: AWS::AccountId
        - Emails
    - EmailSubscription&{Email}:
        Type: AWS::SNS::Subscription
        Properties:
          Protocol: email
          Endpoint:
            Ref: Email
          TopicArn:
            Ref: Topic
"""


def _transform(template_source):
    template = cfn_yaml.loads(template_source)
    return language_extension(
        Template(filename="", template=template, regions=["us-east-1"])
    )


def test_cfnlint_004_language_extensions_reproduction_lints_without_e0001():
    """CFNLINT-004: The reproduction lints successfully without transform E0001."""
    matches = lint(REPRODUCTION_TEMPLATE, regions=["us-east-1"])

    assert matches == []


def test_cfnlint_010_valid_find_in_map_lookups_retain_expected_lint_behavior():
    """CFNLINT-010: Existing valid Fn::FindInMap lint outcomes remain unchanged."""
    template = """\
Transform: AWS::LanguageExtensions
Mappings:
  Environments:
    Production:
      BucketName: production-bucket
Resources:
  Bucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName:
        Fn::FindInMap: [Environments, Production, BucketName]
"""

    assert lint(template, regions=["us-east-1"]) == []


def test_cfnlint_010_valid_for_each_retain_expected_transform_and_lint_behavior():
    """CFNLINT-010: Existing valid Fn::ForEach outcomes remain unchanged."""
    template = """\
Transform: AWS::LanguageExtensions
Resources:
  Fn::ForEach::Buckets:
    - Identifier
    - [One, Two]
    - Bucket${Identifier}:
        Type: AWS::S3::Bucket
"""

    matches, transformed = _transform(template)

    assert lint(template, regions=["us-east-1"]) == []
    assert matches == []
    assert transformed is not None
    assert set(transformed["Resources"]) == {"BucketOne", "BucketTwo"}


def test_cfnlint_011_unquoted_account_id_mapping_array_is_for_each_collection():
    """CFNLINT-011: AWS::AccountId selects an unquoted key's array for iteration."""
    decoded = cfn_yaml.loads(REPRODUCTION_TEMPLATE)
    account_key = next(iter(decoded["Mappings"]["AccountEmails"]))
    collection = decoded["Resources"]["Fn::ForEach::Subscriptions"][1]
    matches, transformed = _transform(REPRODUCTION_TEMPLATE)

    assert account_key == 123456789012
    assert not isinstance(account_key, str)
    assert collection == {
        "Fn::FindInMap": [
            "AccountEmails",
            {"Ref": "AWS::AccountId"},
            "Emails",
        ]
    }
    assert matches == []
    assert transformed is not None
    assert transformed["Resources"]["EmailSubscriptiontesttestcom"]["Properties"][
        "Endpoint"
    ] == "test@test.com"
