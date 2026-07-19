"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from unittest import TestCase

from cfnlint import ConfigMixIn, Rules
from cfnlint.decode import decode_str
from cfnlint.rules.functions.ForEach import ForEach
from cfnlint.runner import TemplateRunner


class TestIssue111MissingTransformDiagnostic(TestCase):
    filename = "issue-111.yaml"

    def _run_foreach_rule(self, source):
        template, decode_matches = decode_str(source)
        self.assertEqual(decode_matches, [])
        self.assertIsNotNone(template)

        rules = Rules()
        rules.register(ForEach())
        runner = TemplateRunner(
            self.filename,
            template,
            ConfigMixIn(regions=["us-east-1"], include_checks=["E"]),
            rules,
        )
        return runner, list(runner.run())

    def test_gev_015_foreach_without_language_extensions_when_e1032_inspects_pretransform_locations_reports_established_diagnostic_at_loop(
        self,
    ):
        """A pre-transform loop without LanguageExtensions reports E1032 at the loop."""
        _, matches = self._run_foreach_rule(
            """AWSTemplateFormatVersion: "2010-09-09"
Resources:
  Fn::ForEach::Topics:
    - Name
    - [One]
    - Topic${Name}:
        Type: AWS::SNS::Topic
"""
        )

        self.assertEqual(len(matches), 1)
        match = matches[0]
        self.assertEqual(match.rule.id, "E1032")
        self.assertEqual(
            match.message,
            "Missing Transform: Declare the AWS::LanguageExtensions Transform "
            "globally to enable use of the intrinsic function Fn::ForEach at "
            "Resources/Fn::ForEach::Topics",
        )
        self.assertEqual(match.path, ["Resources", "Fn::ForEach::Topics"])
        self.assertEqual((match.linenumber, match.columnnumber), (3, 3))

    def test_gev_015_foreach_with_language_extensions_when_e1032_runs_emits_no_missing_transform_and_defers_collection_handling(
        self,
    ):
        """A declared transform suppresses E1032 and retains its collection boundary."""
        runner, matches = self._run_foreach_rule(
            """AWSTemplateFormatVersion: "2010-09-09"
Transform: AWS::LanguageExtensions
Resources:
  Fn::ForEach::Topics:
    - Name
    - [One]
    - Topic${Name}:
        Type: AWS::SNS::Topic
"""
        )

        self.assertEqual(matches, [])
        self.assertEqual(
            runner.cfn.transform_pre["Fn::ForEach"][0][:-1],
            ["Resources", "Fn::ForEach::Topics"],
        )
