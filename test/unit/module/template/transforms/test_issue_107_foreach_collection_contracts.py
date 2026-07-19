"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from unittest import TestCase, skip


class TestIssue107ForEachCollectionContracts(TestCase):
    @skip("GEV-006 absent collection verification placeholder for issue #107")
    def test_gev_006_absent_account_find_in_map_collection_returns_e0001_without_transformed_template(
        self,
    ):
        """An absent requested value fails transformation without output."""
        self.fail("Implement GEV-006 absent collection verification")

    @skip("GEV-006 empty collection verification placeholder for issue #107")
    def test_gev_006_empty_account_find_in_map_collection_returns_e0001_without_transformed_template(
        self,
    ):
        """An empty resolved list fails transformation without output."""
        self.fail("Implement GEV-006 empty collection verification")

    @skip("GEV-006 scalar collection verification placeholder for issue #107")
    def test_gev_006_scalar_account_find_in_map_collection_returns_list_required_e0001(
        self,
    ):
        """A scalar collection reports the established list-required failure."""
        self.fail("Implement GEV-006 scalar collection verification")

    @skip("GEV-006 object collection verification placeholder for issue #107")
    def test_gev_006_object_account_find_in_map_collection_returns_list_required_e0001(
        self,
    ):
        """An object collection reports the established list-required failure."""
        self.fail("Implement GEV-006 object collection verification")

    @skip("GEV-007 unsupported member verification placeholder for issue #107")
    def test_gev_007_unsupported_member_stops_with_collection_value_e0001_without_partial_expansion(
        self,
    ):
        """An unsupported member stops expansion with no partial template."""
        self.fail("Implement GEV-007 unsupported member verification")

    @skip("GEV-007 supported members verification placeholder for issue #107")
    def test_gev_007_supported_string_and_intrinsic_object_members_remain_eligible_for_loop_substitution(
        self,
    ):
        """Supported string and intrinsic-object members remain substitutable."""
        self.fail("Implement GEV-007 supported member verification")
