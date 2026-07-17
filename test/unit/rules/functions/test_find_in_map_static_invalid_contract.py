"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from cfnlint.api import lint
from cfnlint.rules import RulesCollection
from cfnlint.rules.functions.FindInMap import FindInMap


# Architecture boundary: CFNLINT-003, CFNLINT-007.
# Production ownership remains in jsonschema._resolvers_cfn.find_in_map; this module
# owns the regression-case and E1011-observation seam without importing resolver
# internals. Implementation should drive cases through the registered FindInMap rule
# so dependencies flow test -> E1011/BaseFn -> resolver -> mapping context.

TEMPLATE = """\
Mappings:
  ExistingMap:
    ExistingFirstKey:
      ExistingSecondKey: value
Resources:
  Bucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName:
        Fn::FindInMap: %s
"""

REGRESSION_CASES = (
    (
        "missing mapping name",
        '["MissingMap", "ExistingFirstKey", "ExistingSecondKey"]',
        0,
    ),
    (
        "invalid first-level key",
        '["ExistingMap", "MissingFirstKey", "ExistingSecondKey"]',
        1,
    ),
    (
        "invalid second-level key",
        '["ExistingMap", "ExistingFirstKey", "MissingSecondKey"]',
        2,
    ),
)


def _e1011_matches(find_in_map_arguments):
    rules = RulesCollection(include_rules=["E1011"])
    rules.register(FindInMap())

    return [
        match
        for match in lint(TEMPLATE % find_in_map_arguments, rules, ["us-east-1"])
        if match.rule.id == "E1011"
    ]


def _assert_e1011_at_argument(find_in_map_arguments, argument_index):
    matches = _e1011_matches(find_in_map_arguments)

    assert matches, f"Expected E1011 for FindInMap argument {argument_index}"
    assert any(
        match.path[-2:] == ["Fn::FindInMap", argument_index] for match in matches
    ), matches


def test_cfnlint_003_static_missing_mapping_name_validation_emits_e1011_contract():
    """CFNLINT-003: a statically missing mapping name transitions to E1011."""
    # GIVEN a template with a known mapping set and a FindInMap whose statically
    # determinable mapping-name candidate is absent from that set.
    # WHEN the enabled E1011 FindInMap rule validates the expression:
    #   RESOLVE the mapping-name candidate and compare it with the known names.
    #   IF the candidate is absent, COLLECT the mismatch at argument path [0].
    # THEN REQUIRE the collected lint findings to include E1011 for that path.
    # FAILURE: no E1011, a different rule ID, or a different argument path fails
    # this preservation contract.
    _, find_in_map_arguments, argument_index = REGRESSION_CASES[0]

    _assert_e1011_at_argument(find_in_map_arguments, argument_index)


def test_cfnlint_003_static_invalid_selected_mapping_level_key_emits_e1011_contract():
    """CFNLINT-003: a statically invalid selected-level key transitions to E1011."""
    # GIVEN a valid mapping name and a statically determinable key absent from
    # the selected first or second mapping level.
    # WHEN the enabled E1011 FindInMap rule validates each selected-level case:
    #   RESOLVE the key only after its parent mapping level has been selected.
    #   IF the key is absent, COLLECT the mismatch at argument path [1] or [2].
    # THEN REQUIRE every case to produce E1011 at its corresponding key path.
    # FAILURE: accepting an absent key or reporting outside its selected level
    # fails this preservation contract.
    for _, find_in_map_arguments, argument_index in REGRESSION_CASES[1:]:
        _assert_e1011_at_argument(find_in_map_arguments, argument_index)


def test_cfnlint_007_regression_suite_observes_e1011_for_static_invalid_find_in_map():
    """CFNLINT-007: regression cases observe E1011 for static invalid inputs."""
    # GIVEN regression cases for a missing static mapping name and invalid static
    # keys at each selected mapping level.
    # FOR EACH case, RUN the normal lint validation path with E1011 enabled.
    # COLLECT findings by rule ID and FindInMap argument path.
    # IF every case contains its expected E1011 finding:
    #   PASS and preserve the observable evidence for CFNLINT-003.
    # ELSE FAIL with the case whose expected E1011 finding was not observed.
    for case_name, find_in_map_arguments, argument_index in REGRESSION_CASES:
        matches = _e1011_matches(find_in_map_arguments)

        assert matches, f"{case_name} did not produce E1011"
        assert any(
            match.path[-2:] == ["Fn::FindInMap", argument_index]
            for match in matches
        ), f"{case_name} produced E1011 at an unexpected path: {matches!r}"
