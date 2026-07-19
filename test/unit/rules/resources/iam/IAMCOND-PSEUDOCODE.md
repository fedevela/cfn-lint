# Shared IAM Condition procedural contract

This artifact records implementation-ready logic for the shared IAM `Condition`
schema consumed by E3510, E3512, and E3513, including the issue 122 E3510 Runner
and identity-policy entry-point boundaries. It is procedural documentation only;
it does not change runtime behavior. Verification selectors refer to
`test_iam_condition_contract.py` and `test_iamcond_issue_122_contract.py` in this
directory.

## Operator grammar

`RECOGNIZED_CONDITION_OPERATOR` is exactly one of:

- the explicit operators `BinaryEquals`, `Bool`, and `Null`;
- an unqualified base operator from `CONDITION_VALUE_BASES`, optionally followed
  by the literal suffix `Exists`; or
- `ForAllValues:` or `ForAnyValues:` followed by a base operator from
  `CONDITION_VALUE_BASES`, without the `Exists` suffix.

`CONDITION_VALUE_BASES` contains the following complete expansions represented
by the shared schema patterns and the verification matrix:

```text
IpAddress, NotIpAddress,
ArnEquals, ArnNotEquals, ArnLike, ArnNotLike,
DateEquals, DateNotEquals,
NumberLessThan, NumberGreaterThan,
NumberLessThanEquals, NumberGreaterThanEquals,
NumberEquals, NumberNotEquals,
StringEquals, StringNotEquals,
StringEqualsIgnoreCase, StringNotEqualsIgnoreCase,
StringLike, StringNotLike
```

Recognition is a full-name match. Regex anchors belong at the boundaries of the
complete operator name, including any set qualifier. No alias, prefix, suffix,
or partial match is accepted. This explicit rule is significant because the
original `policy.json` set-qualified pattern spellings placed `^` after the
qualifier, and the final `ForAnyValues` string-like pattern spelled `Like?`.
The runtime schema now expresses the grammar above before applying
unknown-member rejection.

## Procedures

```text
PROCEDURE RESOLVE_ISSUE_122_RULE_SELECTION(requested_include_checks)
  REQUIREMENT_IDS: IAMCOND-001, IAMCOND-003
  VERIFICATION:
    test_IAMCOND_001_managed_policy_missing_operator_reports_error_E3510_at_condition_with_normal_and_information_selection[selection-mode]
    test_IAMCOND_003_include_checks_I_preserves_default_error_warning_selection_and_E3510_result

  RECEIVE
    requested_include_checks is empty for normal selection, or contains I for
    --include-checks I

  RESOLVE
    ACTIVE_PREFIXES := [W, E] followed by requested_include_checks in received order
    DO NOT replace W or E when requested_include_checks contains I

  DECIDE
    IF E3510 does not start with any ACTIVE_PREFIX
      TERMINATE without running E3510
    ELSE
      ENABLE E3510 and its E1101 provider-schema parent relationship
    END IF

  RETURN ACTIVE_PREFIXES and the enabled E3510 rule

  INVARIANTS
    Normal selection returns W and E as its first two active prefixes
    --include-checks I returns W, E, and I, so E3510 selection is unchanged
    Selection does not alter E3510.id, E3510.severity, keywords, or findings

  ON FAILURE configuration or template decoding failure
    RETURN the established configuration or parse finding
    DO NOT claim an E3510 identity-policy result for an undecoded template
END PROCEDURE
```

```text
PROCEDURE VALIDATE_ISSUE_122_IDENTITY_POLICY_ENTRY_POINTS(
  template, requested_include_checks
)
  REQUIREMENT_IDS: IAMCOND-001, IAMCOND-003
  VERIFICATION:
    test_IAMCOND_001_managed_policy_missing_operator_reports_error_E3510_at_condition_with_normal_and_information_selection[selection-mode]
    test_IAMCOND_003_missing_operator_is_rejected_beneath_statement_condition_for_each_identity_policy_entry_point[entry-point]
    test_IAMCOND_003_include_checks_I_preserves_default_error_warning_selection_and_E3510_result

  PRECONDITIONS
    template decoded successfully
    each candidate policy is otherwise valid for policy_identity.json
    the malformed Condition maps servicecatalog:accountLevel directly to self

  LOAD
    ACTIVE_PREFIXES, E3510 := RESOLVE_ISSUE_122_RULE_SELECTION(
      requested_include_checks
    )
    REGISTERED_ENTRY_POINTS :=
      AWS::IAM::Group       Properties/Policies/*/PolicyDocument
      AWS::IAM::ManagedPolicy Properties/PolicyDocument
      AWS::IAM::Policy      Properties/PolicyDocument
      AWS::IAM::Role        Properties/Policies/*/PolicyDocument
      AWS::IAM::User        Properties/Policies/*/PolicyDocument
      AWS::SSO::PermissionSet Properties/InlinePolicy
    FINDINGS := empty ordered collection

  DISPATCH
    FOR EACH resource in template.Resources in document order
      IF resource.Type has no entry in REGISTERED_ENTRY_POINTS
        CONTINUE with the next resource
      END IF

      FOR EACH concrete policy document reached through that resource's registered
               property path, expanding each Policies/* element in array order
        DOCUMENT_PATH := Resources / logical-id / concrete property path
        REQUIRE the provider-schema cfnLint keyword at this location to equal the
                corresponding complete keyword registered by IdentityPolicy
        DELEGATE the policy value and current validator context to
                 VALIDATE_IAM_POLICY_DOCUMENT(E3510, policy value, context)

        FOR EACH delegated E3510 finding in schema order
          PREFIX its relative path with DOCUMENT_PATH
          PRESERVE E3510 as its owning rule and error as its severity
          APPEND it to FINDINGS
        END FOR
      END FOR
    END FOR

  CONDITION DECISION
    Within each delegated policy, Statement[0].Condition is present and is an object
    DELEGATE the Condition to VALIDATE_SHARED_CONDITION
    MATCH_RECOGNIZED_CONDITION_OPERATOR(servicecatalog:accountLevel) returns absent
    EMIT E3510 at:
      DOCUMENT_PATH / Statement / 0 / Condition / servicecatalog:accountLevel
    The emitted path is therefore at or beneath the required Condition path

  FILTER / RETURN
    RETAIN every finding whose rule starts with an ACTIVE_PREFIX and is not ignored
    RETURN FINDINGS without requiring an informational finding

  ALTERNATE PATHS
    IF a registered Policies array has multiple elements
      VALIDATE every element independently; one result does not suppress another
    END IF
    IF the same malformed condition enters through any of the six registered paths
      APPLY the same identity schema and unknown-operator decision
    END IF
    IF requested_include_checks contains I
      RETURN the same set of E3510 path/message/severity signatures as normal
      selection; informational rules may add only non-E3510 findings
    END IF

  REPEATED INVOCATION
    Retain no state and mutate neither template nor policy; equivalent inputs and
    selection produce equivalent E3510 signatures

  CONCURRENCY / TRANSACTION / RETRY
    Resource, policy, statement, and condition traversal is synchronous and
    deterministic; no asynchronous completion, persistence, transaction, retry,
    compensation, or rollback applies
END PROCEDURE
```

```text
PROCEDURE CONFIGURE_IAM_POLICY_RULE_FAMILY(rule_id)
  REQUIREMENT_IDS: IAMCOND-008, IAMCOND-010, IAMCOND-013
  VERIFICATION:
    test_IAMCOND_008_recognized_well_structured_condition_remains_valid_per_family
    test_IAMCOND_010_object_and_json_string_representations_have_equivalent_outcomes
    test_IAMCOND_013_condition_finding_does_not_suppress_independent_findings
    test_IAMCOND_013_condition_finding_does_not_suppress_invalid_principal

  DECIDE
    IF rule_id = E3510
      LOAD policy_identity.json as FAMILY_SCHEMA
      REQUIRE Action XOR NotAction, Resource XOR NotResource, and Effect
      DO NOT permit Principal or NotPrincipal
    ELSE IF rule_id = E3512
      LOAD policy_resource.json as FAMILY_SCHEMA
      REQUIRE Action XOR NotAction, Resource XOR NotResource,
              Principal XOR NotPrincipal, and Effect
    ELSE IF rule_id = E3513
      LOAD policy_resource_ecr.json as FAMILY_SCHEMA
      REQUIRE Action XOR NotAction, Principal XOR NotPrincipal, and Effect
      KEEP Resource and NotResource optional
    ELSE
      TERMINATE as unsupported rule configuration
    END IF

  RESOLVE every FAMILY_SCHEMA reference to shared definitions in policy.json
  RETURN FAMILY_SCHEMA and the shared Condition definition
END PROCEDURE
```

```text
PROCEDURE VALIDATE_IAM_POLICY_DOCUMENT(rule_id, policy, incoming_validator_context)
  REQUIREMENT_IDS: IAMCOND-001, IAMCOND-003, IAMCOND-008, IAMCOND-009,
                   IAMCOND-010, IAMCOND-011, IAMCOND-012, IAMCOND-013
  VERIFICATION:
    test_IAMCOND_001_managed_policy_missing_operator_reports_error_E3510_at_condition_with_normal_and_information_selection[selection-mode]
    test_IAMCOND_003_missing_operator_is_rejected_beneath_statement_condition_for_each_identity_policy_entry_point[entry-point]
    test_IAMCOND_008_recognized_well_structured_condition_remains_valid_per_family
    test_IAMCOND_009_supported_intrinsic_in_place_of_condition_operator_is_not_unknown
    test_IAMCOND_009_supported_intrinsics_keep_existing_embedded_policy_outcomes
    test_IAMCOND_010_object_and_json_string_representations_have_equivalent_outcomes
    test_IAMCOND_011_statement_without_optional_condition_has_no_condition_finding
    test_IAMCOND_012_multiple_operators_and_context_keys_remain_accepted
    test_IAMCOND_013_condition_finding_does_not_suppress_independent_findings
    test_IAMCOND_013_condition_finding_does_not_suppress_invalid_principal

  PRECONDITIONS
    rule_id is E3510, E3512, or E3513
    the owning rule has selected this value through one of its registered keywords

  LOAD
    FAMILY_SCHEMA := CONFIGURE_IAM_POLICY_RULE_FAMILY(rule_id)
    ERRORS := empty ordered collection

  NORMALIZE
    IF policy is a string
      PARSE policy as JSON
      IF parsing fails
        RETURN no IAM-schema findings, preserving Policy.validate behavior
      END IF
      DOCUMENT := parsed JSON value
      VALIDATOR_CONTEXT := incoming_validator_context with functions disabled
    ELSE
      DOCUMENT := policy without copying or mutation
      VALIDATOR_CONTEXT := incoming_validator_context unchanged
    END IF

  VALIDATE
    ITERATE every applicable FAMILY_SCHEMA keyword over DOCUMENT
    APPEND every resulting finding to ERRORS; do not stop after the first finding
    FOR EACH Statement selected by the schema
      DELEGATE its optional Condition to VALIDATE_SHARED_CONDITION only when present
      CONTINUE validating Version, statement shape, Effect, Action/NotAction,
               Resource/NotResource, Principal/NotPrincipal where applicable,
               Sid, and unsupported properties independently
    END FOR

  CLASSIFY
    FOR EACH finding in ERRORS
      IF finding.validator starts with "fn_" OR finding.validator = "cfnLint"
        PRESERVE its existing intrinsic or delegated rule ownership
      ELSE
        ASSIGN the owning rule E3510, E3512, or E3513 to the finding
      END IF
    END FOR

  RETURN all ERRORS with their complete schema-produced paths

  REPEATED INVOCATION
    Retain no state and mutate neither DOCUMENT nor schema; equal inputs and
    validator context produce equivalent findings on every invocation

  CONCURRENCY / TRANSACTION / RETRY
    No asynchronous work, persistence, transaction, retry, compensation, or
    rollback applies; validation is synchronous and read-only
END PROCEDURE
```

```text
PROCEDURE VALIDATE_SHARED_CONDITION(condition, path, validator_context)
  REQUIREMENT_IDS: IAMCOND-001, IAMCOND-002, IAMCOND-003, IAMCOND-006,
                   IAMCOND-007, IAMCOND-008, IAMCOND-009, IAMCOND-011,
                   IAMCOND-012, IAMCOND-013
  VERIFICATION:
    test_IAMCOND_001_managed_policy_missing_operator_reports_error_E3510_at_condition_with_normal_and_information_selection[selection-mode]
    test_IAMCOND_002_unknown_top_level_member_is_rejected_beneath_condition
    test_IAMCOND_003_missing_operator_is_rejected_beneath_statement_condition_for_each_identity_policy_entry_point[entry-point]
    test_IAMCOND_006_each_recognized_operator_rejects_a_non_object_body
    test_IAMCOND_007_condition_value_operators_preserve_context_value_shapes
    test_IAMCOND_007_set_operators_preserve_array_only_context_value_shapes
    test_IAMCOND_007_null_operator_preserves_boolean_context_value_shapes
    test_IAMCOND_008_recognized_well_structured_condition_remains_valid_per_family
    test_IAMCOND_009_supported_intrinsic_in_place_of_condition_operator_is_not_unknown
    test_IAMCOND_009_supported_intrinsics_keep_existing_embedded_policy_outcomes
    test_IAMCOND_011_statement_without_optional_condition_has_no_condition_finding
    test_IAMCOND_012_multiple_operators_and_context_keys_remain_accepted
    test_IAMCOND_013_condition_finding_does_not_suppress_independent_findings
    test_IAMCOND_013_condition_finding_does_not_suppress_invalid_principal

  PRECONDITIONS
    this procedure is called only for a present Statement.Condition property
    path ends with Statement / statement-index / Condition

  VALIDATE
    IF condition is not an object
      EMIT the established Condition type finding at path
      RETURN
    END IF

    IF condition has exactly one member AND its name is a supported
       CloudFormation intrinsic in validator_context
      DELEGATE the complete condition value through the existing FunctionFilter
      RETURN its established intrinsic-function findings without an unknown-operator finding
    END IF

    ERRORS := empty ordered collection

    FOR EACH (member_name, member_value) in condition in document order
      IF member_name is a supported CloudFormation intrinsic in validator_context
        PRESERVE the existing additionalProperties intrinsic exemption
        DO NOT classify member_name as an IAM condition operator
        CONTINUE with the next member
      END IF

      OPERATOR_CONTRACT := MATCH_RECOGNIZED_CONDITION_OPERATOR(member_name)
      IF OPERATOR_CONTRACT is absent
        EMIT an additional-property finding at path + member_name
        CONTINUE with the next member
      END IF

      DELEGATE (member_name, member_value, OPERATOR_CONTRACT,
                path + member_name, validator_context)
        to VALIDATE_CONDITION_OPERATOR_BODY
      APPEND every delegated finding to ERRORS
    END FOR

  RETURN all ERRORS

  INVARIANTS
    An empty Condition object remains governed by the established schema behavior
    Multiple recognized operators are evaluated independently
    A failure under one operator does not suppress another operator or statement finding
    Member value shape never changes whether an unknown member name is rejected
END PROCEDURE
```

```text
PROCEDURE MATCH_RECOGNIZED_CONDITION_OPERATOR(member_name)
  REQUIREMENT_IDS: IAMCOND-001, IAMCOND-002, IAMCOND-003, IAMCOND-006,
                   IAMCOND-007, IAMCOND-012
  VERIFICATION:
    test_IAMCOND_001_managed_policy_missing_operator_reports_error_E3510_at_condition_with_normal_and_information_selection[selection-mode]
    test_IAMCOND_002_unknown_top_level_member_is_rejected_beneath_condition
    test_IAMCOND_003_missing_operator_is_rejected_beneath_statement_condition_for_each_identity_policy_entry_point[entry-point]
    test_IAMCOND_006_each_recognized_operator_rejects_a_non_object_body
    test_IAMCOND_007_condition_value_operators_preserve_context_value_shapes
    test_IAMCOND_007_set_operators_preserve_array_only_context_value_shapes
    test_IAMCOND_007_null_operator_preserves_boolean_context_value_shapes
    test_IAMCOND_012_multiple_operators_and_context_keys_remain_accepted

  DECIDE
    IF member_name = Null
      RETURN NULL_BOOLEAN_CONTRACT
    ELSE IF member_name = BinaryEquals OR member_name = Bool
      RETURN CONDITION_VALUE_CONTRACT
    ELSE IF member_name fully matches an unqualified CONDITION_VALUE_BASE
            optionally followed by Exists
      RETURN CONDITION_VALUE_CONTRACT
    ELSE IF member_name fully matches
            (ForAllValues: OR ForAnyValues:) + CONDITION_VALUE_BASE
      RETURN CONDITION_SET_VALUE_CONTRACT
    ELSE
      RETURN absent
    END IF
END PROCEDURE
```

```text
PROCEDURE VALIDATE_CONDITION_OPERATOR_BODY(
  operator_name, operator_body, operator_contract, path, validator_context
)
  REQUIREMENT_IDS: IAMCOND-006, IAMCOND-007, IAMCOND-008, IAMCOND-009,
                   IAMCOND-012
  VERIFICATION:
    test_IAMCOND_006_each_recognized_operator_rejects_a_non_object_body
    test_IAMCOND_007_condition_value_operators_preserve_context_value_shapes
    test_IAMCOND_007_set_operators_preserve_array_only_context_value_shapes
    test_IAMCOND_007_null_operator_preserves_boolean_context_value_shapes
    test_IAMCOND_008_recognized_well_structured_condition_remains_valid_per_family
    test_IAMCOND_009_supported_intrinsics_keep_existing_embedded_policy_outcomes
    test_IAMCOND_012_multiple_operators_and_context_keys_remain_accepted

  VALIDATE
    IF operator_body is not an object
      EMIT an operator-body type finding at path
      RETURN
    END IF

    FOR EACH (context_key, context_value) in operator_body in document order
      IF context_value is a supported CloudFormation intrinsic in validator_context
        DELEGATE to the existing intrinsic-function validator
        PRESERVE its established result and continue
      END IF

      DECIDE
        IF operator_contract = CONDITION_VALUE_CONTRACT
          ACCEPT context_value only when it is:
            a boolean, number, or string; OR
            an array in which every item is a string
        ELSE IF operator_contract = CONDITION_SET_VALUE_CONTRACT
          ACCEPT context_value only when it is an array in which every item is a string
        ELSE IF operator_contract = NULL_BOOLEAN_CONTRACT
          ACCEPT context_value only when it is:
            true, false, "true", or "false"; OR
            an array in which every item is one of those four values
        END IF

      IF context_value was not accepted
        EMIT the established value-shape finding at path + context_key
      END IF
    END FOR

  RETURN every emitted or delegated finding

  INVARIANTS
    Multiple context keys are evaluated independently
    Validation does not normalize, coerce, persist, or mutate context values
END PROCEDURE
```

## Entry-point representation boundary

IAMCOND-010 applies the object/string normalization branch to the ten registered
keywords whose effective provider schema policy admits both representations:

```text
E3510: AWS::IAM::Group Policies/*/PolicyDocument
       AWS::IAM::ManagedPolicy PolicyDocument
       AWS::IAM::Policy PolicyDocument
       AWS::SSO::PermissionSet InlinePolicy
E3512: AWS::KMS::Key KeyPolicy
       AWS::OpenSearchService::Domain AccessPolicies
       AWS::S3::BucketPolicy PolicyDocument
       AWS::SNS::TopicPolicy PolicyDocument
       AWS::SQS::QueuePolicy PolicyDocument
E3513: AWS::ECR::Repository RepositoryPolicyText
```

The E3510 Role and User inline-policy keywords remain outside this matrix because
their `policy_policydocument.json` provider patches intentionally constrain those
properties to object form. The Group patch intentionally admits object/string.

For equivalent JSON-compatible documents, normalization changes only the input
representation. It does not change operator recognition, value contracts,
finding ownership, or the `Statement/Condition/<member>` suffix of finding paths.
Object-form documents additionally retain the incoming CloudFormation intrinsic
context; parsed JSON strings retain the existing functions-disabled behavior.
