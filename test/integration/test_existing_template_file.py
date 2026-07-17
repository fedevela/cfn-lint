"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

import subprocess


def _run_cfn_lint(template):
    return subprocess.run(
        ["cfn-lint", "--", str(template)],
        check=False,
        capture_output=True,
        text=True,
    )


def test_cfnlint_004_existing_clean_template_preserves_workflow_exit_and_diagnostics(
    tmp_path,
):
    """GUID: CFNLINT-004 - A clean existing file retains established results."""
    template = tmp_path / "clean-template.yaml"
    template.write_text(
        'AWSTemplateFormatVersion: "2010-09-09"\nResources: {}\n',
        encoding="utf-8",
    )

    result = _run_cfn_lint(template)

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""


def test_cfnlint_004_existing_findings_preserve_workflow_exit_and_diagnostics(tmp_path):
    """GUID: CFNLINT-004 - Existing-file findings retain established results."""
    template = tmp_path / "template-with-findings.yaml"
    template.write_text("Unexpected: true\nResources: {}\n", encoding="utf-8")

    result = _run_cfn_lint(template)

    assert result.returncode == 2
    assert result.stdout == (
        "E1001 Additional properties are not allowed ('Unexpected' was unexpected)\n"
        f"{template}:1:1\n\n"
    )
    assert result.stderr == ""
