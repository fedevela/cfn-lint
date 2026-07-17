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


def _validate(validator, regions=None, runtime="python3.12"):
    if regions is not None:
        validator = validator.evolve(
            context=validator.context.evolve(regions=regions)
        )
    instance = {**PYTHON_312_SNAPSTART, "Runtime": runtime}
    return list(SnapStartSupported().validate(validator, "", instance, {}))


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


@pytest.mark.parametrize(
    "runtime",
    ["python3.10", "python3.11", "python3.13", "Python3.12"],
)
def test_snapstart_003_other_python_runtimes_remain_rejected_by_e2530(
    validator, runtime
):
    """GUID: SNAPSTART-003."""
    assert _validate(validator, ["us-east-1"], runtime) == [
        ValidationError(
            f"{runtime!r} is not supported for 'SnapStart' enabled functions",
            path=deque(["SnapStart", "ApplyOn"]),
        )
    ]


@pytest.mark.parametrize(
    "runtime,regions,expected",
    [
        (
            "java17",
            ["foo-bar-1"],
            [_unsupported_regions_error(["foo-bar-1"])],
        ),
        (
            "nodejs20.x",
            ["us-east-1"],
            [
                ValidationError(
                    "'nodejs20.x' is not supported for 'SnapStart' enabled functions",
                    path=deque(["SnapStart", "ApplyOn"]),
                )
            ],
        ),
        (
            "python3.11",
            ["foo-bar-1"],
            [
                _unsupported_regions_error(["foo-bar-1"]),
                ValidationError(
                    "'python3.11' is not supported for 'SnapStart' enabled functions",
                    path=deque(["SnapStart", "ApplyOn"]),
                ),
            ],
        ),
        (
            "python3.12",
            ["us-west-1"],
            [_unsupported_regions_error(["us-west-1"])],
        ),
    ],
)
def test_snapstart_004_unsupported_runtime_region_pairs_still_produce_e2530(
    validator, runtime, regions, expected
):
    """GUID: SNAPSTART-004."""
    assert _validate(validator, regions, runtime) == expected


@pytest.mark.parametrize(
    "runtime,region,is_supported",
    [
        ("python3.12", "us-east-1", True),
        ("python3.11", "us-east-1", False),
        ("python3.13", "us-east-1", False),
        ("Python3.12", "us-east-1", False),
        ("python3.12", "us-west-1", False),
    ],
)
def test_snapstart_004_only_python312_supported_region_exits_negative_matrix(
    validator, runtime, region, is_supported
):
    """GUID: SNAPSTART-004."""
    assert (_validate(validator, [region], runtime) == []) is is_supported


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
