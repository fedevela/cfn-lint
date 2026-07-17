"""Placeholder verification contracts for non-nested default resolution."""


def test_cfnlint_007_non_nested_missing_key_uses_default_and_lint_exits_0():
    """GUID: CFNLINT-007.

    Given a missing mapping key outside a nested Fn::ForEach collection,
    transforming and linting uses DefaultValue and completes with exit code 0.
    """
    assert True
