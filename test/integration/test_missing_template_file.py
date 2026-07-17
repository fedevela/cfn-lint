"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

import subprocess


def _run_cfn_lint(missing_template):
    return subprocess.run(
        ["cfn-lint", "--", str(missing_template)],
        check=False,
        capture_output=True,
        text=True,
    )


def test_cfnlint_001_explicit_missing_local_template_path_exits_nonzero(tmp_path):
    """GUID: CFNLINT-001 - A missing explicit local path exits nonzero."""
    result = _run_cfn_lint(tmp_path / "missing-template.yaml")

    assert result.returncode > 0


def test_cfnlint_002_explicit_missing_local_template_path_returns_error_no_traceback(
    tmp_path,
):
    """GUID: CFNLINT-002 - The command returns a deterministic error, not a crash."""
    result = _run_cfn_lint(tmp_path / "missing-template.yaml")

    assert result.returncode > 0
    assert "E0000" in result.stdout
    assert "Traceback" not in result.stderr


def test_cfnlint_003_missing_local_template_stderr_identifies_condition_and_path(
    tmp_path,
):
    """GUID: CFNLINT-003 - Stderr identifies the missing file and affected path."""
    missing_template = tmp_path / "missing-template.yaml"

    result = _run_cfn_lint(missing_template)

    assert "not found" in result.stderr.lower()
    assert str(missing_template) in result.stderr
