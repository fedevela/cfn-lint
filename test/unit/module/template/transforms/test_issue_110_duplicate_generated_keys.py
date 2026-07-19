"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from unittest import TestCase, skip


class TestIssue110DuplicateGeneratedKeys(TestCase):
    @skip("GEV-014 account-collection resource collision placeholder for issue #110")
    def test_gev_014_merging_account_collection_resource_key_collision_returns_duplicate_e0001_without_overwrite(
        self,
    ):
        """A generated Resource collision fails without replacing its existing value."""
        self.fail(
            "Implement GEV-014 account-collection Resource collision verification"
        )

    @skip("GEV-014 account-collection output collision placeholder for issue #110")
    def test_gev_014_merging_account_collection_output_key_collision_returns_duplicate_e0001_without_overwrite(
        self,
    ):
        """A generated Output collision fails without replacing its existing value."""
        self.fail("Implement GEV-014 account-collection Output collision verification")

    @skip("GEV-014 sanitized member collision placeholder for issue #110")
    def test_gev_014_merging_second_sanitized_member_key_collision_returns_duplicate_e0001_without_partial_template(
        self,
    ):
        """A second sanitized-key collision fails without publishing partial output."""
        self.fail("Implement GEV-014 sanitized member-key collision verification")
