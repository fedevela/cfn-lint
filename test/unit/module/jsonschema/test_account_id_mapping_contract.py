"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from collections import deque

from cfnlint.context._mappings import Mappings
from cfnlint.context.context import Context
from cfnlint.decode import decode_str
from cfnlint.jsonschema.validators import CfnTemplateValidator


ACCOUNT_ID = "12345678901"
EMAILS = ["alerts@example.com", "owners@example.com"]
REPRODUCTION = f"""
Mappings:
  AccountEmails:
    {ACCOUNT_ID}:
      Emails:
        - {EMAILS[0]}
        - {EMAILS[1]}
Value:
  Fn::FindInMap:
    - AccountEmails
    - Ref: AWS::AccountId
    - Emails
"""


def _reproduction():
    template, matches = decode_str(REPRODUCTION)
    assert matches == []
    assert template is not None

    context = Context(
        mappings=Mappings.create_from_dict(template["Mappings"]),
        pseudo_parameters=set(),
    )
    validator = CfnTemplateValidator().evolve(context=context)
    return context, validator, template["Value"]


def _resolved_values(validator, expression):
    return [
        (value, resolved_validator.context.path.value_path, error)
        for value, resolved_validator, error in validator.resolve_value(expression)
    ]


def test_cfnlint_001_unquoted_account_id_key_selected_by_account_id_ref():
    """CFNLINT-001: Ref AWS::AccountId selects the unquoted YAML account-ID key."""
    _, validator, expression = _reproduction()

    assert _resolved_values(validator, expression) == [
        (
            EMAILS,
            deque(["Mappings", "AccountEmails", ACCOUNT_ID, "Emails"]),
            None,
        )
    ]


def test_cfnlint_002_complete_account_id_digits_preserved_during_lookup():
    """CFNLINT-002: Lookup preserves the complete account-ID digit sequence."""
    context, validator, expression = _reproduction()

    assert list(context.mappings.maps["AccountEmails"].keys) == [ACCOUNT_ID]
    assert _resolved_values(validator, expression)[0][1][2] == ACCOUNT_ID


def test_cfnlint_009_repeated_lookup_without_aws_context_returns_same_emails():
    """CFNLINT-009: Repeated offline resolution returns the same Emails array."""
    _, validator, expression = _reproduction()

    first = _resolved_values(validator, expression)
    second = _resolved_values(validator, expression)

    assert first == second
    assert [result[0] for result in first] == [EMAILS]
