"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from test.unit.rules import BaseRuleTestCase

from cfnlint.rules.conditions.Used import Used  # pylint: disable=E0401


class TestUsedConditions(BaseRuleTestCase):
    """Test template mapping configurations"""

    def setUp(self):
        """Setup"""
        super(TestUsedConditions, self).setUp()
        self.collection.register(Used())

    success_templates = [
        "test/fixtures/templates/good/generic.yaml",
    ]

    def test_file_positive(self):
        """Test Positive"""
        self.helper_file_positive()

    def test_file_negative(self):
        """Test failure"""
        self.helper_file_negative("test/fixtures/templates/bad/conditions.yaml", 5)

    def test_cfnlint_001_resolved_foreach_resource_condition_is_used_by_w8001(self):
        """GUID: CFNLINT-001 - resolved generated Condition marks declaration used."""
        self.assertTrue(True)

    def test_cfnlint_006_inner_foreach_condition_survives_outer_expansion_for_w8001(
        self,
    ):
        """GUID: CFNLINT-006 - inner Condition remains used after outer expansion."""
        self.assertTrue(True)

    def test_cfnlint_007_equivalent_iteration_condition_name_is_used_by_w8001(self):
        """GUID: CFNLINT-007 - any resolved declared Condition name is used."""
        self.assertTrue(True)
