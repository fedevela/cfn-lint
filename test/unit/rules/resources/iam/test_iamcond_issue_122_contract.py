"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0

Inert verification obligations for issue 122 (IAMCOND-001 and IAMCOND-003).

The cases use the native Runner boundary so rule registration, resource keyword
dispatch, CLI-style selection, severity, and complete finding paths remain part
of the observable contract when Malkhut enables executable validation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cfnlint.config import ConfigMixIn
from cfnlint.runner import Runner
from cfnlint.rules.resources.iam.IdentityPolicy import IdentityPolicy


FIXTURE_DIRECTORY = (
    Path(__file__).parents[4] / "fixtures/templates/bad/resources/iam"
)
MANAGED_POLICY_REPRODUCTION = (
    FIXTURE_DIRECTORY / "managed_policy_missing_condition_operator.yaml"
)
IDENTITY_POLICY_ENTRY_POINT_MATRIX = (
    FIXTURE_DIRECTORY
    / "identity_policy_entry_points_missing_condition_operator.yaml"
)
CONDITION_TAIL = ("Statement", 0, "Condition")

IDENTITY_POLICY_ENTRY_POINTS = (
    pytest.param(
        "Resources/AWS::IAM::Group/Properties/Policies/*/PolicyDocument",
        ("Resources", "IAMGroup", "Properties", "Policies", 0, "PolicyDocument"),
        id="AWS_IAM_Group-Policies-PolicyDocument",
    ),
    pytest.param(
        "Resources/AWS::IAM::ManagedPolicy/Properties/PolicyDocument",
        ("Resources", "IAMManagedPolicy", "Properties", "PolicyDocument"),
        id="AWS_IAM_ManagedPolicy-PolicyDocument",
    ),
    pytest.param(
        "Resources/AWS::IAM::Policy/Properties/PolicyDocument",
        ("Resources", "IAMPolicy", "Properties", "PolicyDocument"),
        id="AWS_IAM_Policy-PolicyDocument",
    ),
    pytest.param(
        "Resources/AWS::IAM::Role/Properties/Policies/*/PolicyDocument",
        ("Resources", "IAMRole", "Properties", "Policies", 0, "PolicyDocument"),
        id="AWS_IAM_Role-Policies-PolicyDocument",
    ),
    pytest.param(
        "Resources/AWS::IAM::User/Properties/Policies/*/PolicyDocument",
        ("Resources", "IAMUser", "Properties", "Policies", 0, "PolicyDocument"),
        id="AWS_IAM_User-Policies-PolicyDocument",
    ),
    pytest.param(
        "Resources/AWS::SSO::PermissionSet/Properties/InlinePolicy",
        ("Resources", "SSOPermissionSet", "Properties", "InlinePolicy"),
        id="AWS_SSO_PermissionSet-InlinePolicy",
    ),
)


def _run_fixture(fixture: Path, extra_cli_args: tuple[str, ...] = ()):
    config = ConfigMixIn(
        ["--template", str(fixture), *extra_cli_args],
    )
    return config, list(Runner(config).run())


def _e3510_matches(matches):
    return [match for match in matches if match.rule.id == "E3510"]


def _is_at_or_beneath(match, expected_path: tuple[object, ...]) -> bool:
    return tuple(match.path[: len(expected_path)]) == expected_path


def _e3510_signatures(matches):
    return {
        (tuple(match.path), match.message, match.rule.severity)
        for match in _e3510_matches(matches)
    }


@pytest.mark.skip(reason="IAMCOND-001 awaits the issue 122 implementation")
@pytest.mark.parametrize(
    "extra_cli_args",
    (
        pytest.param((), id="normal-error-rules"),
        pytest.param(("--include-checks", "I"), id="include-information"),
    ),
)
def test_IAMCOND_001_managed_policy_missing_operator_reports_error_E3510_at_condition_with_normal_and_information_selection(
    extra_cli_args: tuple[str, ...],
) -> None:
    _, matches = _run_fixture(MANAGED_POLICY_REPRODUCTION, extra_cli_args)
    expected_path = (
        "Resources",
        "IAMPolicy",
        "Properties",
        "PolicyDocument",
        *CONDITION_TAIL,
    )

    findings = _e3510_matches(matches)
    assert findings
    assert all(match.rule.severity == "error" for match in findings)
    assert any(_is_at_or_beneath(match, expected_path) for match in findings)


@pytest.mark.skip(reason="IAMCOND-003 awaits the issue 122 implementation")
@pytest.mark.parametrize(
    "registered_keyword,policy_document_path", IDENTITY_POLICY_ENTRY_POINTS
)
def test_IAMCOND_003_missing_operator_is_rejected_beneath_statement_condition_for_each_identity_policy_entry_point(
    registered_keyword: str,
    policy_document_path: tuple[object, ...],
) -> None:
    _, matches = _run_fixture(IDENTITY_POLICY_ENTRY_POINT_MATRIX)
    expected_path = (*policy_document_path, *CONDITION_TAIL)

    assert registered_keyword in IdentityPolicy().keywords
    findings = _e3510_matches(matches)
    finding = next(
        match for match in findings if _is_at_or_beneath(match, expected_path)
    )
    assert finding.rule.severity == "error"


@pytest.mark.skip(reason="IAMCOND-003 awaits the issue 122 implementation")
def test_IAMCOND_003_include_checks_I_preserves_default_error_warning_selection_and_E3510_result() -> None:
    default_config, default_matches = _run_fixture(MANAGED_POLICY_REPRODUCTION)
    information_config, information_matches = _run_fixture(
        MANAGED_POLICY_REPRODUCTION,
        ("--include-checks", "I"),
    )

    assert default_config.include_checks[:2] == ["W", "E"]
    assert information_config.include_checks[:2] == ["W", "E"]
    assert "I" in information_config.include_checks
    assert _e3510_signatures(default_matches)
    assert _e3510_signatures(information_matches) == _e3510_signatures(
        default_matches
    )
