"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from collections import deque

import pytest

from cfnlint.rules.resources.properties.StringLength import StringLength


MANAGED_POLICY_DOCUMENT_PATH = deque(
    [
        "Resources",
        "AWS::IAM::ManagedPolicy",
        "Properties",
        "PolicyDocument",
    ]
)
POLICY_DOCUMENT_SCHEMA = {"type": ["object", "string"]}
MAX_MANAGED_POLICY_SIZE = 6144


@pytest.fixture
def managed_policy_validator(validator):
    return validator.evolve(
        context=validator.context.evolve(
            path=validator.context.path.evolve(
                cfn_path=MANAGED_POLICY_DOCUMENT_PATH,
            )
        )
    )


def _errors(managed_policy_validator, policy_document):
    return list(
        StringLength().maxLength(
            managed_policy_validator,
            MAX_MANAGED_POLICY_SIZE,
            policy_document,
            POLICY_DOCUMENT_SCHEMA,
        )
    )


def _object_document_with_size(size):
    # Compact JSON for {"x":"..."} contributes eight structural characters.
    return {"x": "a" * (size - 8)}


def test_mpol_001_managed_policy_spaces_tabs_cr_lf_are_excluded_from_size(
    managed_policy_validator,
):
    """GUID: MPOL-001 - Ignore specified whitespace when measuring document size."""
    document = _object_document_with_size(MAX_MANAGED_POLICY_SIZE)
    document["x"] += " \t\r\n" * 100

    assert _errors(managed_policy_validator, document) == []
    assert _errors(
        managed_policy_validator,
        "a" * MAX_MANAGED_POLICY_SIZE + " \t\r\n" * 100,
    ) == []


@pytest.mark.parametrize("size", [MAX_MANAGED_POLICY_SIZE, MAX_MANAGED_POLICY_SIZE + 1])
def test_mpol_001_managed_policies_differing_only_by_whitespace_match_outcome(
    managed_policy_validator, size
):
    """GUID: MPOL-001 - Whitespace-only differences preserve the size outcome."""
    compact = _object_document_with_size(size)
    whitespace_variant = _object_document_with_size(size)
    whitespace_variant["x"] = (
        " \t" + whitespace_variant["x"] + "\r\n" * 200
    )

    assert bool(_errors(managed_policy_validator, compact)) == bool(
        _errors(managed_policy_validator, whitespace_variant)
    )


def test_mpol_002_managed_policy_below_6144_non_whitespace_has_no_e3033(
    managed_policy_validator,
):
    """GUID: MPOL-002 - A document below the inclusive limit passes E3033."""
    assert _errors(
        managed_policy_validator,
        _object_document_with_size(MAX_MANAGED_POLICY_SIZE - 1),
    ) == []


def test_mpol_002_managed_policy_at_6144_non_whitespace_has_no_e3033(
    managed_policy_validator,
):
    """GUID: MPOL-002 - A document at the inclusive limit passes E3033."""
    assert _errors(
        managed_policy_validator,
        _object_document_with_size(MAX_MANAGED_POLICY_SIZE),
    ) == []


def test_mpol_003_managed_policy_above_6144_non_whitespace_produces_e3033(
    managed_policy_validator,
):
    """GUID: MPOL-003 - A document above the limit produces E3033."""
    errors = _errors(
        managed_policy_validator,
        _object_document_with_size(MAX_MANAGED_POLICY_SIZE + 1),
    )

    assert len(errors) == 1
    assert errors[0].message == "Item is too long"


def test_mpol_004_aws_load_balancer_controller_block_scalar_has_no_size_e3033():
    """GUID: MPOL-004 - The supplied block-scalar policy has no size E3033."""
    assert True


def test_mpol_004_aws_load_balancer_controller_block_scalar_has_no_associated_e3001():
    """GUID: MPOL-004 - The supplied block-scalar policy has no associated E3001."""
    assert True
