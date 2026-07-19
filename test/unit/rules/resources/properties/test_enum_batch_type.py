"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

import pytest

from cfnlint.rules.resources.properties.Enum import Enum
from cfnlint.rules.resources.properties.Properties import Properties


@pytest.fixture(scope="module")
def rule():
    rule = Properties()
    rule.child_rules["E3030"] = Enum()
    yield rule


def _e3030_findings(rule, validator, resource):
    return [
        finding
        for finding in rule.validate(validator, {}, resource, {})
        if finding.rule is not None and finding.rule.id == "E3030"
    ]


@pytest.mark.parametrize("batch_type", ["managed", "unmanaged"])
def test_batchtype_001_lowercase_resource_type_is_accepted(
    batch_type, rule, validator
):
    """BATCHTYPE-001: lowercase resource-level Type produces no E3030."""
    resource = {
        "Type": "AWS::Batch::ComputeEnvironment",
        "Properties": {"Type": batch_type},
    }

    assert _e3030_findings(rule, validator, resource) == []


@pytest.mark.parametrize("batch_type", ["MANAGED", "UNMANAGED"])
def test_batchtype_002_uppercase_resource_type_remains_accepted(
    batch_type, rule, validator
):
    """BATCHTYPE-002: uppercase resource-level Type remains E3030-compatible."""
    resource = {
        "Type": "AWS::Batch::ComputeEnvironment",
        "Properties": {"Type": batch_type},
    }

    assert _e3030_findings(rule, validator, resource) == []


def test_batchtype_003_unrelated_resource_type_is_rejected(rule, validator):
    """BATCHTYPE-003: an unrelated resource-level Type produces E3030."""
    resource = {
        "Type": "AWS::Batch::ComputeEnvironment",
        "Properties": {"Type": "invalid"},
    }

    findings = _e3030_findings(rule, validator, resource)

    assert len(findings) == 1
    assert list(findings[0].path) == ["Properties", "Type"]
    assert "invalid" in findings[0].message


def test_batchtype_005_lowercase_unrelated_enum_remains_rejected(rule, validator):
    """BATCHTYPE-005: Batch relaxation does not alter ordinary enum casing."""
    resource = {
        "Type": "AWS::Lambda::Function",
        "Properties": {"PackageType": "zip"},
    }

    findings = _e3030_findings(rule, validator, resource)

    assert len(findings) == 1
    assert list(findings[0].path) == ["Properties", "PackageType"]
    assert "zip" in findings[0].message


@pytest.mark.parametrize(
    "compute_resources_type", ["EC2", "FARGATE", "FARGATE_SPOT", "SPOT"]
)
def test_batchtype_006_each_nested_compute_resources_type_is_accepted(
    compute_resources_type, rule, validator
):
    """BATCHTYPE-006: every nested ComputeResources.Type member is accepted."""
    resource = {
        "Type": "AWS::Batch::ComputeEnvironment",
        "Properties": {
            "Type": "MANAGED",
            "ComputeResources": {
                "Type": compute_resources_type,
                "MaxvCpus": 1,
                "Subnets": ["subnet-12345678"],
            },
        },
    }

    assert _e3030_findings(rule, validator, resource) == []


@pytest.mark.parametrize("compute_resources_type", ["ec2", "invalid"])
def test_batchtype_006_nested_type_case_drift_and_unrelated_values_are_rejected(
    compute_resources_type, rule, validator
):
    """BATCHTYPE-006: nested Type rejects case drift and unrelated values."""
    resource = {
        "Type": "AWS::Batch::ComputeEnvironment",
        "Properties": {
            "Type": "MANAGED",
            "ComputeResources": {
                "Type": compute_resources_type,
                "MaxvCpus": 1,
                "Subnets": ["subnet-12345678"],
            },
        },
    }

    findings = _e3030_findings(rule, validator, resource)

    assert len(findings) == 1
    assert list(findings[0].path) == [
        "Properties",
        "ComputeResources",
        "Type",
    ]
    assert compute_resources_type in findings[0].message
