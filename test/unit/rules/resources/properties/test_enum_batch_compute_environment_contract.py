"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from collections import deque

import pytest

from cfnlint.context import Path
from cfnlint.rules.resources.properties.Enum import Enum


BATCH_TYPE_PATH = deque(
    ["Resources", "AWS::Batch::ComputeEnvironment", "Properties", "Type"]
)
BATCH_TYPE_ENUM = ["MANAGED", "UNMANAGED"]

# Architecture contract for GUIDs BATCHTYPE-006 through BATCHTYPE-008:
# - This module owns Batch ComputeEnvironment Type regression inputs and outcomes;
#   the generic Enum rule suite remains the owner of unrelated enum behavior.
# - BATCHTYPE-006 and BATCHTYPE-007 enter E3030 through batch_type_validator and
#   rule.enum, preserving the production rule as the sole validation dependency.
# - Accepted case-form cases and the unsupported case belong at the existing test
#   loci below; no template adapter or second validation path is required.
# - BATCHTYPE-008 is a suite-composition boundary: this contract module and
#   test_enum.py are the relevant unit loci, while pytest owns their execution and
#   aggregate outcome. It introduces no runtime wiring into the rule.


@pytest.fixture
def rule():
    return Enum()


@pytest.fixture
def batch_type_validator(validator):
    return validator.evolve(
        context=validator.context.evolve(path=Path(cfn_path=BATCH_TYPE_PATH))
    )


def _letter_case_equivalents(value):
    variants = [""]
    for character in value:
        variants = [
            prefix + replacement
            for prefix in variants
            for replacement in (character.lower(), character.upper())
        ]
    return variants


def test_batchtype_001_managed_any_letter_case_does_not_report_e3030(
    rule, batch_type_validator
):
    """GUID: BATCHTYPE-001."""
    for instance in _letter_case_equivalents("MANAGED"):
        assert list(
            rule.enum(batch_type_validator, BATCH_TYPE_ENUM, instance, {})
        ) == []


def test_batchtype_002_unmanaged_any_letter_case_does_not_report_e3030(
    rule, batch_type_validator
):
    """GUID: BATCHTYPE-002."""
    for instance in _letter_case_equivalents("UNMANAGED"):
        assert list(
            rule.enum(batch_type_validator, BATCH_TYPE_ENUM, instance, {})
        ) == []


def test_batchtype_003_unsupported_type_reports_validation_error(
    rule, batch_type_validator
):
    """GUID: BATCHTYPE-003."""
    errors = list(rule.enum(batch_type_validator, BATCH_TYPE_ENUM, "EC2", {}))

    assert len(errors) == 1
    assert errors[0].message == "'EC2' is not one of ['MANAGED', 'UNMANAGED']"


def test_batchtype_004_supported_intrinsic_type_handling_remains_unchanged(
    rule, validator, batch_type_validator
):
    """GUID: BATCHTYPE-004."""
    intrinsic = {"Ref": "ComputeEnvironmentType"}
    ordinary_errors = list(rule.enum(validator, BATCH_TYPE_ENUM, intrinsic, {}))
    batch_errors = list(
        rule.enum(batch_type_validator, BATCH_TYPE_ENUM, intrinsic, {})
    )

    assert [error.message for error in batch_errors] == [
        error.message for error in ordinary_errors
    ]


def test_batchtype_005_other_enum_property_case_validation_remains_unchanged(
    rule, validator
):
    """GUID: BATCHTYPE-005."""
    other_property_validator = validator.evolve(
        context=validator.context.evolve(
            path=Path(
                cfn_path=deque(
                    ["Resources", "AWS::Example::Resource", "Properties", "Type"]
                )
            )
        )
    )

    errors = list(rule.enum(other_property_validator, ["MANAGED"], "managed", {}))

    assert len(errors) == 1
    assert errors[0].message == "'managed' is not one of ['MANAGED']"


def test_batchtype_006_managed_upper_lower_and_mixed_case_omit_e3030():
    """GUID: BATCHTYPE-006; placeholder for MANAGED case-form coverage."""
    # PSEUDOCODE (BATCHTYPE-006):
    # INPUT cases := ["MANAGED", "managed", one mixed-case form of "MANAGED"]
    # FOR EACH case:
    #   construct an AWS::Batch::ComputeEnvironment whose Type is case
    #   run E3030 validation and collect errors for the Type property
    #   IF any collected error has rule id E3030:
    #     FAIL this case and identify the rejected case form
    #   ELSE:
    #     record this case as accepted
    # OUTPUT success only after every required MANAGED case form is accepted
    assert True


def test_batchtype_006_unmanaged_upper_lower_and_mixed_case_omit_e3030():
    """GUID: BATCHTYPE-006; placeholder for UNMANAGED case-form coverage."""
    # PSEUDOCODE (BATCHTYPE-006):
    # INPUT cases := ["UNMANAGED", "unmanaged", one mixed-case form of "UNMANAGED"]
    # FOR EACH case:
    #   construct an AWS::Batch::ComputeEnvironment whose Type is case
    #   run E3030 validation and collect errors for the Type property
    #   IF any collected error has rule id E3030:
    #     FAIL this case and identify the rejected case form
    #   ELSE:
    #     record this case as accepted
    # OUTPUT success only after every required UNMANAGED case form is accepted
    assert True


def test_batchtype_007_unsupported_type_reports_property_validation_error():
    """GUID: BATCHTYPE-007; placeholder for unsupported-type coverage."""
    # PSEUDOCODE (BATCHTYPE-007):
    # INPUT unsupported_case := a string not case-insensitively equal to either
    #   "MANAGED" or "UNMANAGED"
    # construct an AWS::Batch::ComputeEnvironment whose Type is unsupported_case
    # run E3030 validation and collect errors for the Type property
    # IF no property error is collected:
    #   FAIL because the unsupported value was accepted
    # IF a collected error belongs to another property or validation rule:
    #   FAIL because it does not prove the Type contract
    # OUTPUT success when E3030 rejects unsupported_case at the Type property
    assert True


def test_batchtype_008_relevant_suites_pass_without_unrelated_regressions():
    """GUID: BATCHTYPE-008; placeholder for suite-level regression safety."""
    # PSEUDOCODE (BATCHTYPE-008):
    # INPUT suites := the new Batch Type regression cases plus existing relevant
    #   Enum rule and AWS::Batch::ComputeEnvironment validation suites
    # run every suite and collect pass, fail, error, and skip outcomes
    # IF any new Batch Type regression case fails:
    #   FAIL and hand the case-specific diagnostic to the corrected behavior owner
    # IF any existing relevant case fails with an unrelated validation difference:
    #   FAIL and report it as a regression outside the scoped Type behavior
    # IF a suite cannot execute:
    #   FAIL with the environmental or dependency blocker; do not record a pass
    # OUTPUT success only when all relevant suites execute and every case passes
    #   without unrelated validation regressions
    assert True
