"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from collections import deque

import pytest

from cfnlint.jsonschema import ValidationError
from cfnlint.rules.resources.lmbd.SnapStartSupported import SnapStartSupported


PYTHON_312_SNAPSTART = {
    "Runtime": "python3.12",
    "SnapStart": {"ApplyOn": "PublishedVersions"},
}


def _validate(validator, regions=None):
    if regions is not None:
        validator = validator.evolve(
            context=validator.context.evolve(regions=regions)
        )
    return list(SnapStartSupported().validate(validator, "", PYTHON_312_SNAPSTART, {}))


def _unsupported_regions_error(regions):
    return ValidationError(
        f"'SnapStart' enabled functions are not supported in {regions!r}",
        path=deque(["SnapStart", "ApplyOn"]),
    )


@pytest.mark.parametrize(
    "region",
    sorted(SnapStartSupported._runtime_region_support["python3.12"]),
)
def test_snapstart_001_python312_in_supported_region_produces_no_e2530(
    validator, region
):
    """GUID: SNAPSTART-001."""
    assert _validate(validator, [region]) == []


def test_snapstart_002_python312_in_only_unsupported_regions_produces_e2530(
    validator,
):
    """GUID: SNAPSTART-002."""
    regions = ["us-west-1", "eu-west-2"]

    assert _validate(validator, regions) == [_unsupported_regions_error(regions)]


def test_snapstart_008_python312_in_mixed_regions_is_evaluated_per_region(validator):
    """GUID: SNAPSTART-008; supported passes and unsupported produces E2530."""
    assert _validate(validator, ["us-east-1", "ap-south-1"]) == [
        _unsupported_regions_error(["ap-south-1"])
    ]


def test_snapstart_009_python312_without_explicit_region_uses_selected_regions(
    validator,
):
    """GUID: SNAPSTART-009; preserve existing region-selection semantics."""
    assert validator.context.regions == ["us-east-1"]
    assert _validate(validator) == []
