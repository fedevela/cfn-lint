"""Tests for rejection of malformed or unresolvable intrinsic expressions."""

from unittest import mock

from cfnlint.config import ConfigMixIn
from cfnlint.runner import TemplateRunner
from cfnlint.template import Template
from cfnlint.template.transforms._language_extensions import language_extension


def _template(find_in_map):
    return {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Transform": "AWS::LanguageExtensions",
        "Mappings": {"Config": {"Production": {"Name": "example"}}},
        "Resources": {
            "Bucket": {
                "Type": "AWS::S3::Bucket",
                "Properties": {"BucketName": {"Fn::FindInMap": find_in_map}},
            }
        },
    }


def _transform(template):
    cfn = Template(filename="", template=template, regions=["us-east-1"])
    return language_extension(cfn)


def test_cfnlint_008_malformed_mapping_remains_invalid_after_transform_error():
    """GUID: CFNLINT-008 - a malformed mapping remains invalid when linted."""
    matches, transformed = _transform(_template({"Map": "Config"}))

    assert transformed is None
    assert [match.rule.id for match in matches] == ["E0001"]
    assert "Fn::FindInMap should be a list" in matches[0].message


def test_cfnlint_008_invalid_default_remains_invalid_after_transform_error():
    """GUID: CFNLINT-008 - an invalid default remains invalid when linted."""
    matches, transformed = _transform(
        _template(["Config", "Missing", "Name", {"Fallback": "example"}])
    )

    assert transformed is None
    assert [match.rule.id for match in matches] == ["E0001"]
    assert "Fn::FindInMap parameter only supports 'DefaultValue'" in matches[0].message


def test_cfnlint_008_unresolvable_intrinsic_remains_invalid_after_transform_error():
    """GUID: CFNLINT-008 - suppression cannot make an unresolved intrinsic valid."""
    template = _template(
        ["Config", {"Fn::GetAtt": ["Bucket", "Arn"]}, "Name"]
    )
    rules = mock.Mock()
    rules.is_rule_enabled.return_value = False
    runner = TemplateRunner(
        filename="template.yaml",
        template=template,
        config=ConfigMixIn(regions=["us-east-1"], ignore_checks=["E0001"]),
        rules=rules,
    )

    assert list(runner.run()) == []
    rules.is_rule_enabled.assert_called_once()
    rules.run.assert_not_called()
    assert runner.cfn.template == template
