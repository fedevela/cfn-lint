"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from __future__ import annotations

import subprocess
from copy import deepcopy
from unittest import TestCase

from cfnlint import ConfigMixIn, lint
from cfnlint.decode import cfn_yaml
from cfnlint.rules import CloudFormationLintRule, Rules
from cfnlint.rules.errors import TransformError
from cfnlint.runner import TemplateRunner


class _TemplateObserver(CloudFormationLintRule):
    id = "W9001"
    shortdesc = "Observe the template supplied to ordinary rules"

    def __init__(self):
        super().__init__()
        self.templates = []

    def initialize(self, cfn):
        self.templates.append(deepcopy(cfn.template))


class TestIssue112SuccessfulExpansionInterfaces(TestCase):
    fixture = "test/fixtures/templates/issues/issue_106_account_keyed_foreach.yaml"

    def _run_cli(self):
        return subprocess.run(  # noqa: S603
            ["cfn-lint", "--", self.fixture],
            check=False,
            capture_output=True,
            text=True,
        )

    def _reproduction(self):
        template = cfn_yaml.load(self.fixture)
        self.assertIsNotNone(template)
        return template

    def _run_with_observer(self, template):
        observer = _TemplateObserver()
        rules = Rules()
        rules.register(TransformError())
        rules.register(observer)
        runner = TemplateRunner(
            self.fixture,
            template,
            ConfigMixIn(regions=["us-east-1"], include_checks=["E", "W"]),
            rules,
        )
        return observer, list(runner.run())

    def _failure_template(self, collections):
        template = self._reproduction()
        template["Mappings"]["AccountMap"] = {
            account: {"Emails": collection}
            for account, collection in collections.items()
        }
        return template

    def test_gev_016_reproduction_yaml_when_cli_runs_ordinary_rules_exits_successfully_without_e0001(
        self,
    ):
        """The CLI exposes successful expansion without a transform diagnostic."""
        result = self._run_cli()

        self.assertEqual(
            result.returncode,
            0,
            f"cfn-lint output:\n{result.stdout}{result.stderr}",
        )
        self.assertNotIn("E0001", result.stdout)
        self.assertNotIn("E0001", result.stderr)

    def test_gev_016_reproduction_text_when_public_lint_runs_normal_rules_returns_no_transform_error_consistent_with_cli(
        self,
    ):
        """The string API exposes the same successful result as the CLI."""
        with open(self.fixture, encoding="utf-8") as fixture:
            matches = lint(fixture.read())
        cli_result = self._run_cli()

        self.assertEqual(matches, [])
        self.assertNotIn("E0001", [match.rule.id for match in matches])
        self.assertEqual(cli_result.returncode, 0)
        self.assertNotIn("E0001", cli_result.stdout + cli_result.stderr)

    def test_gev_016_successful_expansion_when_template_runner_invokes_observer_forwards_generated_subscription_and_removes_foreach(
        self,
    ):
        """An ordinary rule receives only the complete transformed resource model."""
        observer, matches = self._run_with_observer(self._reproduction())

        self.assertEqual(matches, [])
        self.assertEqual(len(observer.templates), 1)
        resources = observer.templates[0]["Resources"]
        self.assertNotIn("Fn::ForEach::Subscriptions", resources)
        self.assertEqual(
            list(observer.templates[0]["Mappings"]["AccountMap"]),
            ["12345678901"],
        )
        self.assertEqual(
            resources["SubscriptionFortesttestcom"]["Properties"]["Endpoint"],
            "test@test.com",
        )

    def test_gev_016_ambiguous_collection_when_template_runner_transforms_returns_established_match_without_invoking_observer(
        self,
    ):
        """Ambiguous account evidence stops rules before any partial template leaks."""
        template = self._failure_template(
            {
                "111111111111": ["one@test.com"],
                "222222222222": ["two@test.com"],
            }
        )

        observer, matches = self._run_with_observer(template)

        self.assertEqual([match.rule.id for match in matches], ["E0001"])
        self.assertIn("Can't resolve Fn::FindInMap", matches[0].message)
        self.assertEqual(observer.templates, [])
        self.assertIn("Fn::ForEach::Subscriptions", template["Resources"])

    def test_gev_016_contract_violating_collection_when_template_runner_transforms_returns_established_match_without_invoking_observer(
        self,
    ):
        """A collection contract violation stops rules before partial publication."""
        template = self._failure_template(
            {
                "111111111111": "one@test.com",
                "222222222222": "one@test.com",
            }
        )

        observer, matches = self._run_with_observer(template)

        self.assertEqual([match.rule.id for match in matches], ["E0001"])
        self.assertIn("Fn::ForEach collection must return a list", matches[0].message)
        self.assertEqual(observer.templates, [])
        self.assertIn("Fn::ForEach::Subscriptions", template["Resources"])
