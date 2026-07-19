"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from unittest import TestCase, skip


class TestIssue109MalformedIntrinsicDiagnostics(TestCase):
    @skip("GEV-012 non-list declaration verification placeholder for issue #109")
    def test_gev_012_non_list_foreach_value_returns_structural_e0001_without_transformed_template(
        self,
    ):
        """A non-list declaration retains the three-element-list diagnostic."""
        self.fail("Implement GEV-012 non-list declaration verification")

    @skip("GEV-012 wrong-arity declaration verification placeholder for issue #109")
    def test_gev_012_wrong_arity_foreach_list_returns_structural_e0001_without_transformed_template(
        self,
    ):
        """A list of any length other than three retains its diagnostic."""
        self.fail("Implement GEV-012 wrong-arity declaration verification")

    @skip("GEV-012 unsupported identifier verification placeholder for issue #109")
    def test_gev_012_unsupported_foreach_identifier_returns_established_e0001_without_transformed_template(
        self,
    ):
        """An unsupported identifier stops transformation with no output."""
        self.fail("Implement GEV-012 unsupported identifier verification")

    @skip("GEV-012 scalar collection verification placeholder for issue #109")
    def test_gev_012_scalar_foreach_collection_returns_list_or_object_e0001_without_transformed_template(
        self,
    ):
        """A scalar collection retains the list-or-object diagnostic."""
        self.fail("Implement GEV-012 scalar collection verification")

    @skip("GEV-012 unsupported object collection placeholder for issue #109")
    def test_gev_012_unsupported_intrinsic_foreach_collection_returns_established_e0001_without_transformed_template(
        self,
    ):
        """An unsupported intrinsic collection stops before account inference."""
        self.fail("Implement GEV-012 unsupported object collection verification")

    @skip("GEV-012 non-object output verification placeholder for issue #109")
    def test_gev_012_non_object_foreach_output_returns_dict_required_e0001_without_transformed_template(
        self,
    ):
        """A non-object loop output retains the object-required diagnostic."""
        self.fail("Implement GEV-012 non-object output verification")

    @skip("GEV-013 non-list FindInMap verification placeholder for issue #109")
    def test_gev_013_non_list_find_in_map_returns_list_required_e0001_before_account_inference(
        self,
    ):
        """A non-list FindInMap is rejected before account inference."""
        self.fail("Implement GEV-013 non-list FindInMap verification")

    @skip("GEV-013 wrong operand count verification placeholder for issue #109")
    def test_gev_013_unsupported_find_in_map_operand_count_returns_arity_e0001_before_account_inference(
        self,
    ):
        """A FindInMap with neither three nor four operands retains its diagnostic."""
        self.fail("Implement GEV-013 FindInMap operand-count verification")

    @skip("GEV-013 non-object DefaultValue verification placeholder for issue #109")
    def test_gev_013_non_object_find_in_map_option_returns_default_value_object_e0001_before_account_inference(
        self,
    ):
        """A non-object fourth operand retains the DefaultValue-object diagnostic."""
        self.fail("Implement GEV-013 non-object DefaultValue verification")

    @skip("GEV-013 malformed DefaultValue object placeholder for issue #109")
    def test_gev_013_option_without_only_default_value_returns_malformed_default_value_e0001_before_account_inference(
        self,
    ):
        """A fourth-operand object may contain only DefaultValue."""
        self.fail("Implement GEV-013 malformed DefaultValue object verification")
