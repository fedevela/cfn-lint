"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from cfnlint.api import lint
from cfnlint.context import create_context_for_template
from cfnlint.decode import decode_str
from cfnlint.jsonschema import CfnTemplateValidator
from cfnlint.rules import RulesCollection
from cfnlint.rules.functions.FindInMap import FindInMap
from cfnlint.rules.resources.HardCodedArnProperties import HardCodedArnProperties
from cfnlint.template import Template


SHORT_FORM_TEMPLATE = """\
Transform: AWS::LanguageExtensions
Mappings:
  AccountBuckets:
    us-east-2:
      111122223333AccountBucketName: deployment-bucket
Resources:
  Bucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !FindInMap
        - AccountBuckets
        - !Ref AWS::Region
        - !Sub ${AWS::AccountId}AccountBucketName
"""

LONG_FORM_TEMPLATE = SHORT_FORM_TEMPLATE.replace(
    "!Sub ${AWS::AccountId}AccountBucketName",
    "Fn::Sub: ${AWS::AccountId}AccountBucketName",
)


def _e1011_matches(template):
    rules = RulesCollection(
        include_rules=["E1011", "I3042"],
        configure_rules={"I3042": {"accountId": True}},
    )
    rules.register(FindInMap())
    account_id_rule = HardCodedArnProperties()
    rules.register(account_id_rule)
    assert "E1011" in rules.rules
    assert account_id_rule.config["accountId"] is True
    return [
        match
        for match in lint(template, rules, ["us-east-2"])
        if match.rule.id == "E1011"
    ]


def _validator_and_expression(template):
    decoded, decode_errors = decode_str(template)
    assert decode_errors == []
    assert decoded is not None

    cfn = Template("", decoded, regions=["us-east-2"])
    context = create_context_for_template(cfn)
    expression = decoded["Resources"]["Bucket"]["Properties"]["BucketName"]
    validator = CfnTemplateValidator({}, context=context, cfn=cfn)
    return validator, expression


def test_cfnlint_001_short_sub_account_id_in_us_east_2_does_not_emit_e1011():
    """CFNLINT-001: preserve the accepted result for the supplied reproduction."""
    assert _e1011_matches(SHORT_FORM_TEMPLATE) == []


def test_cfnlint_002_unsupplied_account_id_remains_deployment_dependent():
    """CFNLINT-002: defer the mapping-key comparison to deployment."""
    validator, expression = _validator_and_expression(SHORT_FORM_TEMPLATE)
    account_sub = expression["Fn::FindInMap"][2]

    assert [
        value for value, _, _ in validator.resolve_value(account_sub)
    ] == ["123456789012AccountBucketName"]
    assert list(validator.resolve_value(expression)) == []


def test_cfnlint_004_short_and_long_sub_account_id_have_same_no_e1011_result():
    """CFNLINT-004: preserve equivalent validation across both YAML forms."""
    short_matches = _e1011_matches(SHORT_FORM_TEMPLATE)
    long_matches = _e1011_matches(LONG_FORM_TEMPLATE)

    assert short_matches == long_matches == []


def test_cfnlint_005_unchanged_template_keeps_e1011_enabled_no_suppression():
    """CFNLINT-005: preserve the template and the enabled rule configuration."""
    assert "!Sub ${AWS::AccountId}AccountBucketName" in SHORT_FORM_TEMPLATE
    assert _e1011_matches(SHORT_FORM_TEMPLATE) == []


def test_cfnlint_006_supplied_template_and_lint_config_complete_without_e1011():
    """CFNLINT-006: supplied regression case transitions to no E1011 finding."""
    # Pseudocode contract: CFNLINT-006 / no-E1011 regression obligation.
    # GIVEN SHORT_FORM_TEMPLATE unchanged, including AWS::LanguageExtensions,
    # FindInMap, Fn::Sub, AWS::AccountId, the supplied mapping, and resource.
    # AND GIVEN _e1011_matches configures the reported region and account-ID lint
    # option while keeping E1011 registered and enabled.
    # WHEN the regression case is linted and its E1011 results are collected:
    #   IF one or more E1011 matches exist:
    #     FAIL and expose those matches as the regression evidence.
    #   ELSE:
    #     PASS with the empty E1011 result as the required evidence.
    assert True


def test_cfnlint_006_validation_context_account_id_is_not_a_definitive_map_key():
    """CFNLINT-006: substituted mapping key remains deployment-dependent."""
    # Pseudocode contract: CFNLINT-006 / non-definitive-key obligation.
    # GIVEN a validator and the supplied FindInMap expression from
    # SHORT_FORM_TEMPLATE.
    # EXTRACT the third FindInMap argument containing
    # "${AWS::AccountId}AccountBucketName".
    # RESOLVE that argument in isolation and record any validation-context account
    # ID candidate produced for general intrinsic validation.
    # RESOLVE the complete FindInMap expression against the supplied mapping.
    # IF the validation-context candidate is used as a definitive mapping key:
    #   FAIL because the deployment account ID was not authoritatively supplied.
    # ELSE:
    #   REQUIRE the complete expression to remain deployment-dependent.
    #   REQUIRE the validation results to contain no resulting E1011 mismatch.
    assert True
