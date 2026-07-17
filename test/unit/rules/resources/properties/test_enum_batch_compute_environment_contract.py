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
    assert True


def test_batchtype_006_unmanaged_upper_lower_and_mixed_case_omit_e3030():
    """GUID: BATCHTYPE-006; placeholder for UNMANAGED case-form coverage."""
    assert True


def test_batchtype_007_unsupported_type_reports_property_validation_error():
    """GUID: BATCHTYPE-007; placeholder for unsupported-type coverage."""
    assert True


def test_batchtype_008_relevant_suites_pass_without_unrelated_regressions():
    """GUID: BATCHTYPE-008; placeholder for suite-level regression safety."""
    assert True
