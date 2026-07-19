"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from unittest import TestCase

from cfnlint.decode import cfn_yaml, convert_dict
from cfnlint.template import Template
from cfnlint.template.transforms._language_extensions import language_extension


class TestIssue106AccountKeyedForEachCollection(TestCase):
    fixture = "test/fixtures/templates/issues/issue_106_account_keyed_foreach.yaml"

    def _transform(self, template):
        return language_extension(
            Template(filename=self.fixture, template=template, regions=["us-east-1"])
        )

    def _template(self, mappings, top_key=None, parameters=None):
        if top_key is None:
            top_key = {"Ref": "AWS::AccountId"}
        template = {
            "Transform": "AWS::LanguageExtensions",
            "Mappings": {"AccountMap": mappings},
            "Resources": {
                "Topic": {"Type": "AWS::SNS::Topic"},
                "Fn::ForEach::Subscriptions": [
                    "Email",
                    {"Fn::FindInMap": ["AccountMap", top_key, "Emails"]},
                    {
                        "SubscriptionFor&{Email}": {
                            "Type": "AWS::SNS::Subscription",
                            "Properties": {
                                "Endpoint": {"Ref": "Email"},
                                "Protocol": "email",
                                "TopicArn": {"Ref": "Topic"},
                            },
                        }
                    },
                ],
            },
        }
        if parameters is not None:
            template["Parameters"] = parameters
        return convert_dict(template)

    def _reproduction(self):
        template = cfn_yaml.load(self.fixture)
        self.assertIsNotNone(template)
        return template

    def _assert_subscription(self, template, logical_id, endpoint):
        subscription = template["Resources"][logical_id]
        self.assertEqual(subscription["Properties"]["Endpoint"], endpoint)

    def test_gev_001_unquoted_account_evidence_resolves_without_e0001_or_synthetic_id(
        self,
    ):
        """Resolve the reproduction from evidence, not ambient account state."""
        source = self._reproduction()
        account_keys = list(source["Mappings"]["AccountMap"])
        self.assertEqual(account_keys, [12345678901])
        self.assertNotIn(123456789012, account_keys)

        matches, transformed = self._transform(source)

        self.assertEqual(matches, [])
        self.assertIsNotNone(transformed)
        self.assertNotIn("E0001", [match.rule.id for match in matches])

    def test_gev_002_gev_003_reproduction_generates_named_subscription_and_endpoint(
        self,
    ):
        """One expansion proves logical-ID sanitization and endpoint substitution."""
        matches, transformed = self._transform(self._reproduction())

        self.assertEqual(matches, [])
        self._assert_subscription(
            transformed, "SubscriptionFortesttestcom", "test@test.com"
        )

    def test_gev_004_identical_account_candidate_lists_expand_once(
        self,
    ):
        """Materially identical supported lists form one unambiguous collection."""
        source = self._template(
            {
                "111111111111": {"Emails": ["one@test.com"]},
                "222222222222": {"Emails": ["one@test.com"]},
            }
        )

        matches, transformed = self._transform(source)

        self.assertEqual(matches, [])
        self.assertEqual(
            set(transformed["Resources"]), {"Topic", "SubscriptionForonetestcom"}
        )
        self._assert_subscription(
            transformed, "SubscriptionForonetestcom", "one@test.com"
        )

    def test_gev_005_different_account_lists_return_e0001_without_template(
        self,
    ):
        """Different candidate lists remain unresolved without partial forwarding."""
        source = self._template(
            {
                "111111111111": {"Emails": ["one@test.com"]},
                "222222222222": {"Emails": ["two@test.com"]},
            }
        )

        matches, transformed = self._transform(source)

        self.assertIsNone(transformed)
        self.assertEqual([match.rule.id for match in matches], ["E0001"])
        self.assertIn("Fn::ForEach::Subscriptions", source["Resources"])

    def test_gev_005_candidates_without_emails_return_e0001_without_template(
        self,
    ):
        """Absent second-level evidence remains unresolved without partial output."""
        source = self._template(
            {
                "111111111111": {"Names": ["one"]},
                "222222222222": {"Names": ["two"]},
            }
        )

        matches, transformed = self._transform(source)

        self.assertIsNone(transformed)
        self.assertEqual([match.rule.id for match in matches], ["E0001"])
        self.assertIn("Fn::ForEach::Subscriptions", source["Resources"])

    def test_gev_008_literal_key_keeps_exact_entry_over_account_inference(
        self,
    ):
        """An exact literal lookup takes precedence over account inference."""
        source = self._template(
            {
                "Exact": {"Emails": ["exact@test.com"]},
                "Other": {"Emails": ["other@test.com"]},
            },
            "Exact",
        )

        matches, transformed = self._transform(source)

        self.assertEqual(matches, [])
        self._assert_subscription(
            transformed, "SubscriptionForexacttestcom", "exact@test.com"
        )

    def test_gev_008_parameter_default_keeps_exact_entry_over_account_inference(
        self,
    ):
        """An exactly default-derived lookup takes precedence over inference."""
        source = self._template(
            {
                "Exact": {"Emails": ["default@test.com"]},
                "Other": {"Emails": ["other@test.com"]},
            },
            {"Ref": "AccountKey"},
            {"AccountKey": {"Type": "String", "Default": "Exact"}},
        )

        matches, transformed = self._transform(source)

        self.assertEqual(matches, [])
        self._assert_subscription(
            transformed, "SubscriptionFordefaulttestcom", "default@test.com"
        )

    def test_gev_008_allowed_value_keeps_exact_entry_over_account_inference(
        self,
    ):
        """An exactly allowed-value-derived lookup takes precedence over inference."""
        source = self._template(
            {
                "Exact": {"Emails": ["allowed@test.com"]},
                "Other": {"Emails": ["other@test.com"]},
            },
            {"Ref": "AccountKey"},
            {"AccountKey": {"Type": "String", "AllowedValues": ["Exact"]}},
        )

        matches, transformed = self._transform(source)

        self.assertEqual(matches, [])
        self._assert_subscription(
            transformed, "SubscriptionForallowedtestcom", "allowed@test.com"
        )

    def test_gev_017_quoted_and_unquoted_account_keys_expand_identically(
        self,
    ):
        """YAML key representation does not change collection resolution."""
        unquoted = self._reproduction()
        quoted = cfn_yaml.loads(
            """
Transform: AWS::LanguageExtensions
Mappings:
  AccountMap:
    "12345678901":
      Emails:
        - test@test.com
Resources:
  Topic:
    Type: AWS::SNS::Topic
  Fn::ForEach::Subscriptions:
    - Email
    - Fn::FindInMap:
        - AccountMap
        - Ref: AWS::AccountId
        - Emails
    - SubscriptionFor&{Email}:
        Type: AWS::SNS::Subscription
        Properties:
          Endpoint:
            Ref: Email
          Protocol: email
          TopicArn:
            Ref: Topic
"""
        )
        self.assertIsInstance(next(iter(unquoted["Mappings"]["AccountMap"])), int)
        self.assertIsInstance(next(iter(quoted["Mappings"]["AccountMap"])), str)

        unquoted_matches, unquoted_result = self._transform(unquoted)
        quoted_matches, quoted_result = self._transform(quoted)

        self.assertEqual(unquoted_matches, [])
        self.assertEqual(quoted_matches, [])
        self.assertEqual(unquoted_result["Resources"], quoted_result["Resources"])
        self._assert_subscription(
            quoted_result, "SubscriptionFortesttestcom", "test@test.com"
        )
