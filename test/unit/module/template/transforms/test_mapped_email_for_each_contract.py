"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from cfnlint.decode import convert_dict
from cfnlint.template import Template
from cfnlint.template.transforms._language_extensions import language_extension


ACCOUNT_ID = "123456789012"
SINGLE_EMAIL = "test@test.com"


def _transform_mapped_emails(emails):
    template = convert_dict(
        {
            "Transform": "AWS::LanguageExtensions",
            "Mappings": {"AccountEmails": {ACCOUNT_ID: {"Emails": emails}}},
            "Resources": {
                "Fn::ForEach::Subscriptions": [
                    "Email",
                    {
                        "Fn::FindInMap": [
                            "AccountEmails",
                            {"Ref": "AWS::AccountId"},
                            "Emails",
                        ]
                    },
                    {
                        "EmailSubscription&{Email}": {
                            "Type": "AWS::SNS::Subscription",
                            "Properties": {
                                "Protocol": "email",
                                "Endpoint": {"Ref": "Email"},
                                "TopicArn": {"Ref": "Topic"},
                            },
                        }
                    },
                ]
            },
        }
    )
    matches, transformed = language_extension(
        Template(filename="", template=template, regions=["us-east-1"])
    )
    return matches, transformed


def _subscriptions(transformed):
    return {
        logical_id: resource
        for logical_id, resource in transformed["Resources"].items()
        if resource["Type"] == "AWS::SNS::Subscription"
    }


def test_cfnlint_003_resolved_mapping_emails_array_is_accepted_as_for_each_collection():
    """CFNLINT-003: A resolved mapped Emails array is accepted for iteration."""
    matches, transformed = _transform_mapped_emails([SINGLE_EMAIL])

    assert matches == []
    assert transformed is not None
    assert "Fn::ForEach::Subscriptions" not in transformed["Resources"]


def test_cfnlint_005_single_mapped_email_generates_exactly_one_sns_subscription():
    """CFNLINT-005: Transforming test@test.com creates one SNS subscription."""
    matches, transformed = _transform_mapped_emails([SINGLE_EMAIL])

    assert matches == []
    assert len(_subscriptions(transformed)) == 1


def test_cfnlint_006_resolved_email_is_substituted_into_subscription_identifier():
    """CFNLINT-006: Each resolved email appears in its resource identifier."""
    matches, transformed = _transform_mapped_emails([SINGLE_EMAIL])

    assert matches == []
    assert set(_subscriptions(transformed)) == {"EmailSubscriptiontesttestcom"}


def test_cfnlint_007_resolved_email_is_substituted_into_subscription_endpoint():
    """CFNLINT-007: Each resolved email becomes its subscription Endpoint."""
    matches, transformed = _transform_mapped_emails([SINGLE_EMAIL])

    assert matches == []
    subscription = next(iter(_subscriptions(transformed).values()))
    assert subscription["Properties"]["Endpoint"] == SINGLE_EMAIL


def test_cfnlint_008_multiple_mapped_emails_generate_distinct_matching_subscriptions():
    """CFNLINT-008: Each mapped email gets a distinct resource, ID, and Endpoint."""
    emails = ["alerts@example.com", "owners@example.org"]
    matches, transformed = _transform_mapped_emails(emails)

    assert matches == []
    subscriptions = _subscriptions(transformed)
    assert {
        logical_id: resource["Properties"]["Endpoint"]
        for logical_id, resource in subscriptions.items()
    } == {
        "EmailSubscriptionalertsexamplecom": emails[0],
        "EmailSubscriptionownersexampleorg": emails[1],
    }
