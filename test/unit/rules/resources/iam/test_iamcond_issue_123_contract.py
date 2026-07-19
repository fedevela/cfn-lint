"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0

Verification coverage for issue 123 (IAMCOND-004).

The cases use the native Runner boundary so E3512 registration, resource
keyword dispatch, attribution, and complete resource-relative finding paths
remain part of the observable contract exercised by the Atlas harness.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cfnlint.config import ConfigMixIn
from cfnlint.runner import Runner
from cfnlint.rules.resources.iam.ResourcePolicy import ResourcePolicy


FIXTURE_ROOT = Path(__file__).parents[4] / "fixtures/templates"
MISSING_OPERATOR_MATRIX = (
    FIXTURE_ROOT
    / "bad/resources/iam/resource_policy_entry_points_missing_condition_operator.yaml"
)
RECOGNIZED_CONDITION_MATRIX = (
    FIXTURE_ROOT
    / "good/resources/iam/resource_policy_entry_points_recognized_condition.yaml"
)
CONDITION_TAIL = ("Statement", 0, "Condition")
OFFENDING_MEMBER = "servicecatalog:accountLevel"

RESOURCE_POLICY_ENTRY_POINTS = (
    pytest.param(
        "Resources/AWS::KMS::Key/Properties/KeyPolicy",
        ("Resources", "KMSKey", "Properties", "KeyPolicy"),
        id="AWS_KMS_Key-KeyPolicy",
    ),
    pytest.param(
        "Resources/AWS::OpenSearchService::Domain/Properties/AccessPolicies",
        ("Resources", "OpenSearchDomain", "Properties", "AccessPolicies"),
        id="AWS_OpenSearchService_Domain-AccessPolicies",
    ),
    pytest.param(
        "Resources/AWS::S3::BucketPolicy/Properties/PolicyDocument",
        ("Resources", "S3BucketPolicy", "Properties", "PolicyDocument"),
        id="AWS_S3_BucketPolicy-PolicyDocument",
    ),
    pytest.param(
        "Resources/AWS::SNS::TopicPolicy/Properties/PolicyDocument",
        ("Resources", "SNSTopicPolicy", "Properties", "PolicyDocument"),
        id="AWS_SNS_TopicPolicy-PolicyDocument",
    ),
    pytest.param(
        "Resources/AWS::SQS::QueuePolicy/Properties/PolicyDocument",
        ("Resources", "SQSQueuePolicy", "Properties", "PolicyDocument"),
        id="AWS_SQS_QueuePolicy-PolicyDocument",
    ),
)


def _run_fixture(fixture: Path):
    config = ConfigMixIn(["--template", str(fixture)])
    return list(Runner(config).run())


def _e3512_matches(matches):
    return [match for match in matches if match.rule.id == "E3512"]


def _is_at_or_beneath(match, expected_path: tuple[object, ...]) -> bool:
    return tuple(match.path[: len(expected_path)]) == expected_path


@pytest.mark.parametrize(
    "registered_keyword,policy_document_path", RESOURCE_POLICY_ENTRY_POINTS
)
def test_IAMCOND_004_missing_operator_is_rejected_by_E3512_at_the_offending_condition_member_for_each_resource_policy_entry_point(
    registered_keyword: str,
    policy_document_path: tuple[object, ...],
) -> None:
    matches = _run_fixture(MISSING_OPERATOR_MATRIX)
    expected_path = (
        *policy_document_path,
        *CONDITION_TAIL,
        OFFENDING_MEMBER,
    )

    assert registered_keyword in ResourcePolicy().keywords
    finding = next(
        match
        for match in _e3512_matches(matches)
        if tuple(match.path) == expected_path
    )
    assert finding.rule.severity == "error"


@pytest.mark.parametrize(
    "registered_keyword,policy_document_path", RESOURCE_POLICY_ENTRY_POINTS
)
def test_IAMCOND_004_recognized_nested_condition_has_no_missing_operator_E3512_finding_for_each_resource_policy_entry_point(
    registered_keyword: str,
    policy_document_path: tuple[object, ...],
) -> None:
    matches = _run_fixture(RECOGNIZED_CONDITION_MATRIX)
    expected_path = (*policy_document_path, *CONDITION_TAIL)

    assert registered_keyword in ResourcePolicy().keywords
    assert not any(
        _is_at_or_beneath(match, expected_path)
        for match in _e3512_matches(matches)
    )
