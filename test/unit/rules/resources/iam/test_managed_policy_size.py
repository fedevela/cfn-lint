"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

import json

from cfnlint import ConfigMixIn, Rules
from cfnlint.rules.jsonschema.CfnLint import CfnLint
from cfnlint.rules.jsonschema.JsonSchema import JsonSchema
from cfnlint.rules.resources.Configuration import Configuration
from cfnlint.rules.resources.iam.IdentityPolicy import IdentityPolicy
from cfnlint.rules.resources.properties.Properties import Properties
from cfnlint.rules.resources.properties.StringLength import StringLength
from cfnlint.runner import TemplateRunner


def _policy_document_json_variants(compact_length):
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "service:Action",
                "Resource": "",
            }
        ],
    }
    empty_resource_length = len(json.dumps(policy_document, separators=(",", ":")))
    policy_document["Statement"][0]["Resource"] = "a" * (
        compact_length - empty_resource_length
    )

    compact = json.dumps(policy_document, separators=(",", ":"))
    whitespace = json.dumps(policy_document, indent=4)

    assert len(compact) == compact_length
    assert len(whitespace) > len(compact)
    assert json.loads(compact) == json.loads(whitespace)

    return compact, whitespace


def _managed_policy_size_errors(validator, policy_document_json):
    rule = Properties()
    rule.child_rules["E3033"] = StringLength()
    resource = {
        "Type": "AWS::IAM::ManagedPolicy",
        "Properties": {"PolicyDocument": json.loads(policy_document_json)},
    }

    return [
        error
        for error in rule.validate(validator, {}, resource, {})
        if error.rule.id == "E3033"
        and list(error.path) == ["Properties", "PolicyDocument"]
    ]


def _iammp_005_supplied_reproduction_errors(validator):
    template = {
        "Resources": {
            "OversizedManagedPolicy": {
                "Type": "AWS::IAM::ManagedPolicy",
                "Properties": {
                    "PolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": "service:Action",
                                "Resource": "a" * 6144,
                            }
                        ],
                    }
                },
            }
        }
    }
    rule = Properties()
    rule.child_rules["E3033"] = StringLength()

    return list(
        rule.validate(
            validator,
            {},
            template["Resources"]["OversizedManagedPolicy"],
            {},
        )
    )


def _iammp_008_errors(compact_length):
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Invalid",
                "Action": "service:Action",
                "Resource": "*",
                "Sid": "",
            }
        ],
    }
    empty_resource_length = len(json.dumps(policy_document, separators=(",", ":")))
    policy_document["Statement"][0]["Sid"] = "a" * (
        compact_length - empty_resource_length
    )
    template = {
        "Resources": {
            "ManagedPolicy": {
                "Type": "AWS::IAM::ManagedPolicy",
                "Properties": {"PolicyDocument": policy_document},
            }
        }
    }
    rules = Rules()
    rules.register(JsonSchema())
    rules.register(CfnLint())
    rules.register(Configuration())
    rules.register(Properties())
    rules.register(StringLength())
    rules.register(IdentityPolicy())

    assert len(json.dumps(policy_document, separators=(",", ":"))) == compact_length

    return list(
        TemplateRunner(
            filename=None,
            template=template,
            config=ConfigMixIn(regions=["us-east-1"]),
            rules=rules,
        ).run()
    )


def _iammp_009_size_errors():
    policy_documents = {
        "OversizedManagedPolicyOne": json.loads(
            _policy_document_json_variants(6145)[0]
        ),
        "CompliantManagedPolicy": json.loads(
            _policy_document_json_variants(6144)[0]
        ),
        "OversizedManagedPolicyTwo": json.loads(
            _policy_document_json_variants(6146)[0]
        ),
    }
    template = {
        "Resources": {
            name: {
                "Type": "AWS::IAM::ManagedPolicy",
                "Properties": {"PolicyDocument": policy_document},
            }
            for name, policy_document in policy_documents.items()
        }
    }
    rules = Rules()
    rules.register(JsonSchema())
    rules.register(CfnLint())
    rules.register(Configuration())
    rules.register(Properties())
    rules.register(StringLength())

    return [
        error
        for error in TemplateRunner(
            filename=None,
            template=template,
            config=ConfigMixIn(regions=["us-east-1"]),
            rules=rules,
        ).run()
        if error.rule.id == "E3033"
    ]


def test_iammp_001_static_managed_policy_compact_over_6144_reports_policy_doc_error(
    validator,
):
    """IAMMP-001: oversized static managed policies report a PolicyDocument error."""
    rule = Properties()
    rule.child_rules["E3033"] = StringLength()
    resource = {
        "Type": "AWS::IAM::ManagedPolicy",
        "Properties": {
            "PolicyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": "service:Action",
                        "Resource": "a" * 6144,
                    }
                ],
            }
        },
    }

    errors = list(rule.validate(validator, {}, resource, {}))

    assert len(errors) == 1
    assert errors[0].message == "Item is too long"
    assert list(errors[0].path) == ["Properties", "PolicyDocument"]
    assert errors[0].rule.id == "E3033"


def test_iammp_002_validating_compact_managed_policy_at_6144_does_not_report_size_error(
    validator,
):
    """IAMMP-002: an exact-limit compact PolicyDocument has no size-limit error."""
    rule = Properties()
    rule.child_rules["E3033"] = StringLength()
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "service:Action",
                "Resource": "",
            }
        ],
    }
    compact_length = len(json.dumps(policy_document, separators=(",", ":")))
    policy_document["Statement"][0]["Resource"] = "a" * (6144 - compact_length)
    resource = {
        "Type": "AWS::IAM::ManagedPolicy",
        "Properties": {"PolicyDocument": policy_document},
    }

    assert len(json.dumps(policy_document, separators=(",", ":"))) == 6144

    errors = list(rule.validate(validator, {}, resource, {}))
    size_errors = [
        error
        for error in errors
        if error.rule.id == "E3033"
        and list(error.path) == ["Properties", "PolicyDocument"]
    ]

    assert size_errors == []


def test_iammp_003_validating_compact_managed_policy_below_6144_does_not_report_size_error(
    validator,
):
    """IAMMP-003: a below-limit compact PolicyDocument has no size-limit error."""
    rule = Properties()
    rule.child_rules["E3033"] = StringLength()
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "service:Action",
                "Resource": "",
            }
        ],
    }
    compact_length = len(json.dumps(policy_document, separators=(",", ":")))
    policy_document["Statement"][0]["Resource"] = "a" * (6143 - compact_length)
    resource = {
        "Type": "AWS::IAM::ManagedPolicy",
        "Properties": {"PolicyDocument": policy_document},
    }

    assert len(json.dumps(policy_document, separators=(",", ":"))) == 6143

    errors = list(rule.validate(validator, {}, resource, {}))
    size_errors = [
        error
        for error in errors
        if error.rule.id == "E3033"
        and list(error.path) == ["Properties", "PolicyDocument"]
    ]

    assert size_errors == []


def test_iammp_004_whitespace_only_policy_changes_preserve_size_validation_result(
    validator,
):
    """IAMMP-004: insignificant whitespace does not change the size result."""
    compact, whitespace = _policy_document_json_variants(6144)

    compact_errors = _managed_policy_size_errors(validator, compact)
    whitespace_errors = _managed_policy_size_errors(validator, whitespace)

    assert compact_errors == whitespace_errors == []


def test_iammp_004_oversized_compact_and_whitespace_policy_both_report_size_error(
    validator,
):
    """IAMMP-004: both oversized formatting variants report a size error."""
    compact, whitespace = _policy_document_json_variants(6145)

    for policy_document_json in (compact, whitespace):
        errors = _managed_policy_size_errors(validator, policy_document_json)

        assert len(errors) == 1
        assert errors[0].message == "Item is too long"


def test_iammp_004_compliant_compact_and_whitespace_policy_neither_report_size_error(
    validator,
):
    """IAMMP-004: neither compliant formatting variant reports a size error."""
    compact, whitespace = _policy_document_json_variants(6143)
    assert len(whitespace) > 6144

    for policy_document_json in (compact, whitespace):
        assert _managed_policy_size_errors(validator, policy_document_json) == []


def test_iammp_005_validating_supplied_reproduction_reports_template_invalid(
    validator,
):
    """IAMMP-005: the supplied reproduction is reported invalid."""
    errors = _iammp_005_supplied_reproduction_errors(validator)

    assert errors


def test_iammp_005_supplied_oversized_managed_policy_reports_policy_doc_size_error(
    validator,
):
    """IAMMP-005: the oversized ManagedPolicy reports a PolicyDocument size error."""
    errors = _iammp_005_supplied_reproduction_errors(validator)

    assert len(errors) == 1
    assert errors[0].message == "Item is too long"
    assert list(errors[0].path) == ["Properties", "PolicyDocument"]
    assert errors[0].rule.id == "E3033"


def test_iammp_006_oversized_aws_iam_managedpolicy_applies_6144_character_limit(
    validator,
):
    """IAMMP-006: an oversized ManagedPolicy is subject to the 6,144 limit."""
    compact, _ = _policy_document_json_variants(6145)

    errors = _managed_policy_size_errors(validator, compact)

    assert len(errors) == 1
    assert errors[0].message == "Item is too long"
    assert list(errors[0].path) == ["Properties", "PolicyDocument"]
    assert errors[0].rule.id == "E3033"


def test_iammp_006_oversized_non_managedpolicy_resource_is_not_reported_by_6144_limit(
    validator,
):
    """IAMMP-006: the managed-policy size check excludes other resource types."""
    compact, _ = _policy_document_json_variants(6145)
    rule = Properties()
    rule.child_rules["E3033"] = StringLength()
    resource = {
        "Type": "AWS::IAM::Policy",
        "Properties": {
            "PolicyDocument": json.loads(compact),
            "PolicyName": "InlinePolicy",
            "Roles": ["ExampleRole"],
        },
    }

    errors = [
        error
        for error in rule.validate(validator, {}, resource, {})
        if error.rule.id == "E3033"
        and list(error.path) == ["Properties", "PolicyDocument"]
    ]

    assert errors == []


def test_iammp_007_validating_managed_policy_with_unresolved_final_compact_content_does_not_report_estimated_size_error(
    validator,
):
    """IAMMP-007: unresolved final content is not rejected by a size estimate."""
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "service:Action",
                "Resource": {"Ref": "UnresolvedResource"},
                "Sid": "a" * 6144,
            }
        ],
    }
    estimated_policy_document = {
        **policy_document,
        "Statement": [{**policy_document["Statement"][0], "Resource": ""}],
    }
    rule = Properties()
    rule.child_rules["E3033"] = StringLength()
    resource = {
        "Type": "AWS::IAM::ManagedPolicy",
        "Properties": {"PolicyDocument": policy_document},
    }

    assert (
        len(json.dumps(estimated_policy_document, separators=(",", ":"))) > 6144
    )

    errors = [
        error
        for error in rule.validate(validator, {}, resource, {})
        if error.rule.id == "E3033"
        and list(error.path) == ["Properties", "PolicyDocument"]
    ]

    assert errors == []


def test_iammp_008_oversized_managed_policy_reports_size_error_and_preserves_other_applicable_lint_rule(
):
    """IAMMP-008: size failure preserves every other applicable lint rule."""
    errors = _iammp_008_errors(6145)

    assert [error.rule.id for error in errors] == ["E3033", "E3510"]
    assert errors[0].message == "Item is too long"
    assert errors[0].path == [
        "Resources",
        "ManagedPolicy",
        "Properties",
        "PolicyDocument",
    ]
    assert errors[1].message == "'Invalid' is not one of ['Allow', 'Deny']"
    assert errors[1].path == [
        "Resources",
        "ManagedPolicy",
        "Properties",
        "PolicyDocument",
        "Statement",
        0,
        "Effect",
    ]


def test_iammp_008_compliant_managed_policy_omits_size_error_and_preserves_other_applicable_lint_rule(
):
    """IAMMP-008: size success preserves every other applicable lint rule."""
    errors = _iammp_008_errors(6144)

    assert [error.rule.id for error in errors] == ["E3510"]
    assert errors[0].message == "'Invalid' is not one of ['Allow', 'Deny']"
    assert errors[0].path == [
        "Resources",
        "ManagedPolicy",
        "Properties",
        "PolicyDocument",
        "Statement",
        0,
        "Effect",
    ]


def test_iammp_009_validating_multiple_managed_policies_identifies_every_oversized_policy_document(
):
    """IAMMP-009: every oversized policy in a multi-policy template is identified."""
    errors = _iammp_009_size_errors()

    assert [error.message for error in errors] == [
        "Item is too long",
        "Item is too long",
    ]
    assert [error.path for error in errors] == [
        [
            "Resources",
            "OversizedManagedPolicyOne",
            "Properties",
            "PolicyDocument",
        ],
        [
            "Resources",
            "OversizedManagedPolicyTwo",
            "Properties",
            "PolicyDocument",
        ],
    ]


def test_iammp_009_validating_multiple_managed_policies_does_not_identify_compliant_policy_documents_as_oversized(
):
    """IAMMP-009: compliant policies in a multi-policy template are not identified."""
    errors = _iammp_009_size_errors()

    assert {error.path[1] for error in errors} == {
        "OversizedManagedPolicyOne",
        "OversizedManagedPolicyTwo",
    }


# IAMMP-010 architecture boundary:
# - this focused test module owns the managed-policy size regression matrix;
#   each named test below is one matrix cell and remains independently attributable
#   to its over-limit, exact-limit, under-limit, whitespace, or reproduction case;
# - _policy_document_json_variants is the test-fixture construction port for the
#   three threshold cells and the whitespace-equivalence cell, keeping boundary
#   data generation separate from validation and diagnostic selection;
# - _managed_policy_size_errors is the validation adapter for those four cells;
#   it alone binds the test matrix to Properties -> schema maxLength -> E3033 and
#   exposes only size diagnostics at the PolicyDocument boundary;
# - _iammp_005_supplied_reproduction_errors is the reproduction adapter reused by
#   the fifth cell, preserving the supplied resource shape while exposing the full
#   validation result needed to establish invalidity and its causal size error;
# - StringLength/E3033 remains the production owner of compact-size comparison;
#   these tests own regression evidence only and must not duplicate that behavior.
# Dependency direction is matrix cell -> test fixture/adapter -> Properties/schema
# dispatch -> StringLength/E3033 -> path-preserving diagnostic. The reproduction
# cell depends on its dedicated adapter rather than on synthetic boundary fixtures;
# no production module may depend on this test-only matrix or its helpers.
def test_iammp_010_over_limit_managed_policy_reports_size_limit_error(validator):
    """IAMMP-010: an over-limit policy must report the size-limit error."""
    # IAMMP-010 logic obligation: over-limit regression branch.
    # INPUT: construct a statically determinable managed PolicyDocument whose
    # compact JSON representation is one character greater than the 6,144
    # character maximum.
    # TRANSITION:
    #   1. Hand the document to the managed-policy size-validation flow.
    #   2. Retain only the E3033 result located at Properties/PolicyDocument.
    # DECISION: IF the compact size is greater than the maximum, require one
    # size-limit error; ELSE this regression branch fails.
    # OUTPUT: verify that the retained result reports "Item is too long" at the
    # managed policy's PolicyDocument locus.
    # FAILURE PATH: reject a missing, duplicated, differently located, or
    # differently classified size-limit result.
    compact, _ = _policy_document_json_variants(6145)

    errors = _managed_policy_size_errors(validator, compact)

    assert len(errors) == 1
    assert errors[0].message == "Item is too long"
    assert list(errors[0].path) == ["Properties", "PolicyDocument"]
    assert errors[0].rule.id == "E3033"


def test_iammp_010_exactly_at_limit_managed_policy_does_not_report_size_limit_error(
    validator,
):
    """IAMMP-010: an exactly-at-limit policy must not report a size error."""
    # IAMMP-010 logic obligation: exactly-at-limit regression branch.
    # INPUT: construct a statically determinable managed PolicyDocument whose
    # compact JSON representation is exactly 6,144 characters.
    # TRANSITION: hand the document through the same managed-policy validation
    # and E3033-at-PolicyDocument filtering flow used by the over-limit branch.
    # DECISION: IF the compact size equals the maximum, require an empty filtered
    # result; IF any size-limit result remains, this regression branch fails.
    # OUTPUT: verify equality is accepted without a managed-policy size error.
    # FAILURE PATH: do not treat equality as overflow, and do not use the absence
    # of unrelated lint results as the success criterion.
    compact, _ = _policy_document_json_variants(6144)

    errors = _managed_policy_size_errors(validator, compact)

    assert errors == []


def test_iammp_010_under_limit_managed_policy_does_not_report_size_limit_error(
    validator,
):
    """IAMMP-010: an under-limit policy must not report a size-limit error."""
    # IAMMP-010 logic obligation: under-limit regression branch.
    # INPUT: construct a statically determinable managed PolicyDocument whose
    # compact JSON representation is one character below the 6,144 maximum.
    # TRANSITION: hand the document through managed-policy size validation and
    # retain only E3033 results at Properties/PolicyDocument.
    # DECISION: IF the compact size is below the maximum, require an empty
    # filtered result; IF a size-limit result remains, this branch fails.
    # OUTPUT: verify the compliant document contributes no size-limit error.
    # FAILURE PATH: preserve independently applicable lint results rather than
    # interpreting or suppressing them as managed-policy size failures.
    compact, _ = _policy_document_json_variants(6143)

    errors = _managed_policy_size_errors(validator, compact)

    assert errors == []


def test_iammp_010_formatting_only_whitespace_changes_do_not_alter_size_validation_result(
    validator,
):
    """IAMMP-010: formatting-only whitespace must not alter the size result."""
    # IAMMP-010 logic obligation: whitespace-insensitive regression branch.
    # INPUT: derive compact and whitespace-expanded JSON texts that deserialize
    # to the same PolicyDocument and have an identical 6,144-character compact
    # representation, while the expanded source text exceeds 6,144 characters.
    # TRANSITION:
    #   1. Validate the document deserialized from the compact text.
    #   2. Validate the document deserialized from the expanded text.
    #   3. Filter each result to E3033 at Properties/PolicyDocument.
    # DECISION: compare the two filtered results; formatting-only whitespace
    # must not change their presence, message, count, or path.
    # OUTPUT: verify both variants produce the same no-size-error result.
    # FAILURE PATH: fail if source formatting changes the result or if the
    # expanded source-text length is mistaken for compact policy size.
    compact, whitespace = _policy_document_json_variants(6144)
    assert len(whitespace) > 6144

    compact_errors = _managed_policy_size_errors(validator, compact)
    whitespace_errors = _managed_policy_size_errors(validator, whitespace)

    assert compact_errors == whitespace_errors == []


def test_iammp_010_supplied_reproduction_is_invalid_when_oversized_managed_policy_reports_policy_document_size_error(
    validator,
):
    """IAMMP-010: the oversized reproduction must fail with a policy size error."""
    # IAMMP-010 logic obligation: supplied-reproduction regression branch.
    # INPUT: use the supplied template reproduction containing its oversized,
    # statically determinable AWS::IAM::ManagedPolicy PolicyDocument.
    # TRANSITION:
    #   1. Execute the applicable validation flow for the reproduced resource.
    #   2. Collect the resulting errors without mutating the reproduction.
    #   3. Locate the E3033 size error at Properties/PolicyDocument.
    # DECISION: IF exactly one matching "Item is too long" result exists, mark
    # the reproduction invalid for policy-document size; ELSE this branch fails.
    # OUTPUT: verify both template invalidity and its causal PolicyDocument size
    # error, preserving the resource/property locus in the reported path.
    # FAILURE PATH: reject validity inferred from unrelated errors, a size error
    # at another path, or validation that silently accepts the oversized policy.
    errors = _iammp_005_supplied_reproduction_errors(validator)
    size_errors = [
        error
        for error in errors
        if error.rule.id == "E3033"
        and list(error.path) == ["Properties", "PolicyDocument"]
    ]

    assert errors
    assert len(size_errors) == 1
    assert size_errors[0].message == "Item is too long"
