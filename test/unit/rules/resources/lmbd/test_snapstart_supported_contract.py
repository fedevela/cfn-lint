"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from collections import deque

import pytest

from cfnlint.jsonschema import ValidationError
from cfnlint.rules.resources.lmbd.SnapStartSupported import SnapStartSupported
from cfnlint.template.transforms._sam import Transform


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


def _transformed_sam_function_properties(region, *, inherit_runtime=False):
    function_properties = {
        "CodeUri": ".",
        "Handler": "index.handler",
        "SnapStart": {"ApplyOn": "PublishedVersions"},
    }
    template = {
        "Transform": "AWS::Serverless-2016-10-31",
        "Resources": {
            "Function": {
                "Type": "AWS::Serverless::Function",
                "Properties": function_properties,
            }
        },
    }
    if inherit_runtime:
        template["Globals"] = {"Function": {"Runtime": "python3.12"}}
    else:
        function_properties["Runtime"] = "python3.12"

    transform = Transform("", template, region)
    assert transform.transform_template() == []

    function = transform.template()["Resources"]["Function"]
    assert function["Type"] == "AWS::Lambda::Function"
    return function["Properties"]


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


def test_snapstart_005_existing_valid_java_runtime_region_remains_accepted(validator):
    """GUID: SNAPSTART-005."""
    assert _validate(validator, ["us-east-1"], "java17") == []


def test_snapstart_005_java_result_uses_java_boundary_when_python312_differs(
    validator,
):
    """GUID: SNAPSTART-005."""
    region = "us-west-1"
    rule = SnapStartSupported()

    assert region in rule.regions
    assert region not in rule._runtime_region_support["python3.12"]
    assert _validate(validator, [region], "java17") == []


@pytest.mark.parametrize(
    "runtime,region",
    [
        ("java11", "us-east-1"),
        ("java17", "eu-west-1"),
        ("java21", "ap-south-1"),
    ],
)
def test_snapstart_005_existing_java_acceptance_cases_remain_valid(
    validator, runtime, region
):
    """GUID: SNAPSTART-005."""
    assert _validate(validator, [region], runtime) == []


def test_snapstart_006_sam_function_python312_property_in_supported_region_has_no_e2530(
    validator,
):
    """GUID: SNAPSTART-006; direct SAM runtime survives transformation."""
    properties = _transformed_sam_function_properties("us-east-1")

    assert properties["Runtime"] == "python3.12"
    assert list(SnapStartSupported().validate(validator, "", properties, {})) == []


def test_snapstart_006_sam_function_python312_globals_in_supported_region_has_no_e2530(
    validator,
):
    """GUID: SNAPSTART-006; inherited SAM runtime survives transformation."""
    properties = _transformed_sam_function_properties(
        "us-east-1", inherit_runtime=True
    )

    assert properties["Runtime"] == "python3.12"
    assert list(SnapStartSupported().validate(validator, "", properties, {})) == []


def test_snapstart_007_direct_and_sam_lint_supported_region_both_have_no_e2530(
    validator,
):
    """GUID: SNAPSTART-007; equivalent supported configurations have parity."""
    sam_properties = _transformed_sam_function_properties("us-east-1")
    sam_results = list(
        SnapStartSupported().validate(validator, "", sam_properties, {})
    )

    assert _validate(validator, ["us-east-1"]) == sam_results == []


def test_snapstart_007_direct_and_sam_lint_unsupported_region_match_e2530_rejection(
    validator,
):
    """GUID: SNAPSTART-007; equivalent unsupported configurations have parity."""
    region = "us-west-1"
    unsupported_validator = validator.evolve(
        context=validator.context.evolve(regions=[region])
    )
    sam_properties = _transformed_sam_function_properties(region)
    sam_results = list(
        SnapStartSupported().validate(
            unsupported_validator, "", sam_properties, {}
        )
    )

    assert _validate(validator, [region]) == sam_results == [
        _unsupported_regions_error([region])
    ]


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
