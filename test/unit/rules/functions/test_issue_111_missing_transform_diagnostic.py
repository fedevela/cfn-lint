"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from unittest import TestCase, skip


class TestIssue111MissingTransformDiagnostic(TestCase):
    @skip("GEV-015 missing LanguageExtensions diagnostic placeholder for issue #111")
    def test_gev_015_foreach_without_language_extensions_when_e1032_inspects_pretransform_locations_reports_established_diagnostic_at_loop(
        self,
    ):
        """A pre-transform loop without LanguageExtensions reports E1032 at the loop."""
        self.fail("Implement GEV-015 missing-transform E1032 location verification")

    @skip("GEV-015 declared LanguageExtensions boundary placeholder for issue #111")
    def test_gev_015_foreach_with_language_extensions_when_e1032_runs_emits_no_missing_transform_and_defers_collection_handling(
        self,
    ):
        """A declared transform suppresses E1032 and retains its collection boundary."""
        self.fail("Implement GEV-015 declared-transform rule-boundary verification")
