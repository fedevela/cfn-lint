"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0

Normal-workflow verification for empty Fn::ForEach collections.
"""

from test.integration import BaseCliTestCase


class TestForEach001LiteralEmptyCollectionWorkflow(BaseCliTestCase):
    scenarios = [
        {
            "filename": (
                "test/fixtures/templates/issues/foreach_empty_collection_literal.yaml"
            ),
            "results": [],
            "exit_code": 0,
        }
    ]

    def test_foreach_001_literal_empty_collection_lints_without_e0001(self):
        """GUID: FOREACH-001; normal cfn-lint workflow accepts literal []."""
        self.run_scenarios()


class TestForEach002FindInMapEmptyCollectionWorkflow(BaseCliTestCase):
    scenarios = [
        {
            "filename": (
                "test/fixtures/templates/issues/"
                "foreach_empty_collection_find_in_map.yaml"
            ),
            "results": [],
            "exit_code": 0,
        }
    ]

    def test_foreach_002_find_in_map_empty_collection_lints_without_e0001(self):
        """GUID: FOREACH-002; normal cfn-lint workflow accepts resolved []."""
        self.run_scenarios()
