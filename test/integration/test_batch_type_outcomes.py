"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

import json
import subprocess

import pytest
import yaml

from cfnlint import lint
from cfnlint.config import ManualArgs
from cfnlint.helpers import REGION_PRIMARY, REGIONS
from cfnlint.schema import PROVIDER_SCHEMA_MANAGER


RESOURCE_TYPE = "AWS::Batch::ComputeEnvironment"
RESOURCE_TYPE_PATH = ["Resources", "BatchEnvironment", "Properties", "Type"]
ACCEPTED_BATCH_TYPES = ["managed", "unmanaged", "MANAGED", "UNMANAGED"]
INVALID_BATCH_TYPE = "invalid"


def _template(batch_type):
    return {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "BatchEnvironment": {
                "Type": RESOURCE_TYPE,
                "Properties": {"Type": batch_type},
            }
        },
    }


def _encode_template(batch_type, template_format):
    template = _template(batch_type)
    if template_format == "json":
        return json.dumps(template)
    return yaml.safe_dump(template, sort_keys=False)


def _api_e3030(batch_type, region, template_format="yaml"):
    return [
        (match.rule.id, list(match.path))
        for match in lint(
            _encode_template(batch_type, template_format),
            config=ManualArgs(regions=[region]),
        )
        if match.rule.id == "E3030"
    ]


def _cli_e3030(batch_type, region, template_format, tmp_path):
    template_path = tmp_path / f"batch-type.{template_format}"
    template_path.write_text(
        _encode_template(batch_type, template_format), encoding="utf-8"
    )
    result = subprocess.run(
        [
            "cfn-lint",
            "--format",
            "json",
            "--regions",
            region,
            "--",
            str(template_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    findings = json.loads(result.stdout)
    e3030_findings = [
        (finding["Rule"]["Id"], finding["Location"]["Path"])
        for finding in findings
        if finding["Rule"]["Id"] == "E3030"
    ]
    assert result.returncode == (2 if e3030_findings else 0), result.stderr
    return e3030_findings


def _supported_batch_regions():
    return [
        region
        for region in REGIONS
        if RESOURCE_TYPE in PROVIDER_SCHEMA_MANAGER.get_resource_types(region)
    ]


def _assert_supported_region_grouping(supported_regions):
    groups = list(
        PROVIDER_SCHEMA_MANAGER.get_resource_schemas_by_regions(
            RESOURCE_TYPE, supported_regions
        )
    )
    grouped_regions = [region for regions, _ in groups for region in regions]
    cached_regions = [
        region
        for region in supported_regions
        if PROVIDER_SCHEMA_MANAGER.get_resource_schema(
            region, RESOURCE_TYPE
        ).is_cached
    ]
    primary_schema_group = next(
        regions for regions, _ in groups if REGION_PRIMARY in regions
    )

    assert sorted(grouped_regions) == sorted(supported_regions)
    assert len(grouped_regions) == len(set(grouped_regions))
    assert REGION_PRIMARY in grouped_regions
    assert cached_regions
    assert set(cached_regions).issubset(primary_schema_group)


def test_batchtype_004_every_supported_region_including_cached_primary_accepts_all_four_resource_type_spellings(
):
    """BATCHTYPE-004: all supported schema regions accept the four spellings."""
    supported_regions = _supported_batch_regions()
    _assert_supported_region_grouping(supported_regions)

    assert supported_regions
    for region in supported_regions:
        for batch_type in ACCEPTED_BATCH_TYPES:
            assert _api_e3030(batch_type, region) == []


def test_batchtype_004_every_supported_region_rejects_invalid_value_at_resource_type_path(
):
    """BATCHTYPE-004: all supported regions reject invalid resource Type."""
    supported_regions = _supported_batch_regions()
    _assert_supported_region_grouping(supported_regions)

    assert supported_regions
    for region in supported_regions:
        assert _api_e3030(INVALID_BATCH_TYPE, region) == [
            ("E3030", RESOURCE_TYPE_PATH)
        ]


@pytest.mark.parametrize("batch_type", ACCEPTED_BATCH_TYPES + [INVALID_BATCH_TYPE])
def test_batchtype_009_cli_and_python_api_agree_on_resource_type_acceptance_or_rejection(
    batch_type, tmp_path
):
    """BATCHTYPE-009: CLI and lint API expose identical Type outcomes."""
    cli_findings = _cli_e3030(batch_type, REGION_PRIMARY, "yaml", tmp_path)
    api_findings = _api_e3030(batch_type, REGION_PRIMARY, "yaml")

    assert cli_findings == api_findings
    assert bool(cli_findings) is (batch_type == INVALID_BATCH_TYPE)


@pytest.mark.parametrize("batch_type", ACCEPTED_BATCH_TYPES + [INVALID_BATCH_TYPE])
def test_batchtype_011_equivalent_json_and_yaml_have_identical_resource_type_rule_ids_and_outcomes(
    batch_type,
):
    """BATCHTYPE-011: JSON and YAML decoding preserve Type validation parity."""
    json_findings = _api_e3030(batch_type, REGION_PRIMARY, "json")
    yaml_findings = _api_e3030(batch_type, REGION_PRIMARY, "yaml")

    assert json_findings == yaml_findings
    assert [rule_id for rule_id, _ in json_findings] == (
        ["E3030"] if batch_type == INVALID_BATCH_TYPE else []
    )


def test_batchtype_009_011_invalid_cli_api_json_yaml_findings_identify_resource_type_not_nested_type(
    tmp_path,
):
    """BATCHTYPE-009/011: every invalid execution reports resource Type path."""
    executions = {
        "cli-json": _cli_e3030(
            INVALID_BATCH_TYPE, REGION_PRIMARY, "json", tmp_path
        ),
        "cli-yaml": _cli_e3030(
            INVALID_BATCH_TYPE, REGION_PRIMARY, "yaml", tmp_path
        ),
        "api-json": _api_e3030(INVALID_BATCH_TYPE, REGION_PRIMARY, "json"),
        "api-yaml": _api_e3030(INVALID_BATCH_TYPE, REGION_PRIMARY, "yaml"),
    }

    assert executions
    assert all(
        findings == [("E3030", RESOURCE_TYPE_PATH)]
        for findings in executions.values()
    )
    assert all("ComputeResources" not in path for _, path in executions["api-yaml"])
