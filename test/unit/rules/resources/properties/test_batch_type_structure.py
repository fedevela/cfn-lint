"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

import pytest

from cfnlint.rules.resources.properties.Enum import Enum
from cfnlint.rules.resources.properties.Properties import Properties
from cfnlint.rules.resources.properties.Required import Required
from cfnlint.rules.resources.properties.Type import Type


@pytest.fixture(scope="module")
def rule():
    rule = Properties()
    rule.child_rules["E3003"] = Required()
    rule.child_rules["E3012"] = Type()
    rule.child_rules["E3030"] = Enum()
    yield rule


def _findings(rule, validator, properties):
    resource = {
        "Type": "AWS::Batch::ComputeEnvironment",
        "Properties": properties,
    }
    return list(rule.validate(validator, {}, resource, {}))


def test_batchtype_007_omitted_resource_type_emits_e3003_at_properties_boundary(
    rule, validator
):
    """BATCHTYPE-007: omission emits E3003 at the resource Properties boundary."""
    findings = _findings(rule, validator, {})

    required_findings = [
        finding
        for finding in findings
        if finding.rule is not None and finding.rule.id == "E3003"
    ]
    assert len(required_findings) == 1
    assert list(required_findings[0].path) == ["Properties"]
    assert "'Type' is a required property" in required_findings[0].message


def test_batchtype_008_null_resource_type_emits_e3012_string_contract_finding(
    rule, validator
):
    """BATCHTYPE-008: null emits E3012 for the resource Type string contract."""
    findings = _findings(rule, validator, {"Type": None})

    type_findings = [
        finding
        for finding in findings
        if finding.rule is not None and finding.rule.id == "E3012"
    ]
    assert len(type_findings) == 1
    assert list(type_findings[0].path) == ["Properties", "Type"]
    assert "None is not of type 'string'" in type_findings[0].message


@pytest.mark.parametrize(
    "non_string_type",
    [
        pytest.param(True, id="boolean"),
        pytest.param(1.5, id="number"),
        pytest.param([], id="array"),
        pytest.param({}, id="object"),
    ],
)
def test_batchtype_008_non_string_literal_emits_finding_and_is_not_accepted(
    non_string_type, rule, validator
):
    """BATCHTYPE-008: non-strings emit E3012/E3030 despite casing relaxation."""
    findings = _findings(rule, validator, {"Type": non_string_type})

    structural_findings = [
        finding
        for finding in findings
        if finding.rule is not None and finding.rule.id in {"E3012", "E3030"}
    ]
    assert structural_findings
    assert all(
        list(finding.path) == ["Properties", "Type"]
        for finding in structural_findings
    )


@pytest.mark.parametrize("accepted_type", ["managed", "MANAGED"])
def test_batchtype_007_008_accepted_string_passes_structure_and_preserves_domain(
    accepted_type, rule, validator
):
    """BATCHTYPE-007/008: accepted strings pass structure and retain E3030."""
    accepted_findings = _findings(rule, validator, {"Type": accepted_type})
    invalid_findings = _findings(rule, validator, {"Type": "invalid"})

    assert accepted_findings == []
    enum_findings = [
        finding
        for finding in invalid_findings
        if finding.rule is not None and finding.rule.id == "E3030"
    ]
    assert len(enum_findings) == 1
    assert list(enum_findings[0].path) == ["Properties", "Type"]
