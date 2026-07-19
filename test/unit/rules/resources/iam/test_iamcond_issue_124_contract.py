"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0

Inert verification obligations for issue 124 (IAMCOND-005).

The cases use the native Runner boundary so E3513 registration, ECR repository
policy dispatch, attribution, statement semantics, and the complete
resource-relative finding path remain observable when Malkhut enables
executable validation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cfnlint.config import ConfigMixIn
from cfnlint.runner import Runner
from cfnlint.rules.resources.iam.ResourceEcrPolicy import ResourceEcrPolicy


FIXTURE_ROOT = Path(__file__).parents[4] / "fixtures/templates"
MISSING_OPERATOR_POLICY = (
    FIXTURE_ROOT
    / "bad/resources/iam/ecr_repository_policy_missing_condition_operator.yaml"
)
RECOGNIZED_CONDITION_POLICY = (
    FIXTURE_ROOT
    / "good/resources/iam/ecr_repository_policy_recognized_condition.yaml"
)
REGISTERED_KEYWORD = (
    "Resources/AWS::ECR::Repository/Properties/RepositoryPolicyText"
)
REPOSITORY_POLICY_PATH = (
    "Resources",
    "ECRRepository",
    "Properties",
    "RepositoryPolicyText",
)
CONDITION_TAIL = ("Statement", 0, "Condition")
OFFENDING_MEMBER = "servicecatalog:accountLevel"


def _run_fixture(fixture: Path):
    config = ConfigMixIn(["--template", str(fixture)])
    return list(Runner(config).run())


def _e3513_matches(matches):
    return [match for match in matches if match.rule.id == "E3513"]


def _is_at_or_beneath(match, expected_path: tuple[object, ...]) -> bool:
    return tuple(match.path[: len(expected_path)]) == expected_path


@pytest.mark.skip(reason="IAMCOND-005 awaits the issue 124 implementation")
def test_IAMCOND_005_missing_operator_is_rejected_by_E3513_at_the_offending_ECR_repository_policy_condition_member() -> None:
    matches = _run_fixture(MISSING_OPERATOR_POLICY)
    expected_path = (
        *REPOSITORY_POLICY_PATH,
        *CONDITION_TAIL,
        OFFENDING_MEMBER,
    )

    assert REGISTERED_KEYWORD in ResourceEcrPolicy().keywords
    finding = next(
        match
        for match in _e3513_matches(matches)
        if tuple(match.path) == expected_path
    )
    assert finding.rule.severity == "error"


@pytest.mark.skip(reason="IAMCOND-005 awaits the issue 124 implementation")
def test_IAMCOND_005_recognized_nested_condition_has_no_missing_operator_E3513_finding_and_preserves_ECR_statement_acceptance() -> None:
    matches = _run_fixture(RECOGNIZED_CONDITION_POLICY)
    expected_path = (*REPOSITORY_POLICY_PATH, *CONDITION_TAIL)
    e3513_matches = _e3513_matches(matches)

    assert REGISTERED_KEYWORD in ResourceEcrPolicy().keywords
    assert not any(
        _is_at_or_beneath(match, expected_path) for match in e3513_matches
    )
    assert e3513_matches == []
