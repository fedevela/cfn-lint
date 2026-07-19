# Issue 136 IAM Condition Operator Logic

This artifact specifies the implementation logic for the shared IAM Condition
schema used by E3510. It changes no runtime behavior by itself.

## Operator families

The ordered `SET_QUALIFIED_FAMILIES` and `IF_EXISTS_FAMILIES` collections both
contain these 20 canonical comparison operator names:

```text
IpAddress
NotIpAddress
ArnEquals
ArnNotEquals
ArnLike
ArnNotLike
DateEquals
DateNotEquals
NumericLessThan
NumericLessThanEquals
NumericGreaterThan
NumericGreaterThanEquals
NumericEquals
NumericNotEquals
StringEquals
StringNotEquals
StringEqualsIgnoreCase
StringNotEqualsIgnoreCase
StringLike
StringNotLike
```

`SET_QUALIFIERS` contains exactly `ForAnyValue:` and `ForAllValues:`. These
names are case-sensitive and singular in `Value`.

## Procedure: define_shared_condition_operator_patterns

```text
PROCEDURE define_shared_condition_operator_patterns()
  REQUIREMENT_IDS: IAMCOND-001, IAMCOND-002, IAMCOND-003, IAMCOND-004,
                   IAMCOND-005
  VERIFICATION:
    test_iamcond_001_given_string_or_string_array_when_string_equals_if_exists_then_e3510_accepts
    test_iamcond_002_given_string_array_when_for_any_value_string_equals_then_e3510_accepts
    test_iamcond_003_given_string_array_when_for_all_values_string_equals_then_e3510_accepts
    test_iamcond_004_given_supported_comparison_family_when_correct_set_qualifier_and_array_values_then_shared_condition_accepts
    test_iamcond_005_given_non_set_comparison_family_when_if_exists_with_established_values_then_shared_condition_accepts

  PRECONDITIONS
    LOAD the shared schema at
      src/cfnlint/data/schemas/other/iam/policy.json
    RECOGNIZE that policy_identity.json (E3510) and policy_resource.json
      (E3512) both resolve Condition through this shared definition
    PRESERVE Condition.additionalProperties as false
    PRESERVE ConditionSetValue and ConditionValue without widening or narrowing
      either value contract

  BUILD SET-QUALIFIED RECOGNITION
    FOR EACH qualifier IN SET_QUALIFIERS, in declared order
      FOR EACH family IN SET_QUALIFIED_FAMILIES, in declared order
        operator_name := CONCAT(qualifier, family)
        DECLARE one patternProperties entry that matches operator_name from the
          beginning through the end of the property name
        DELEGATE the matched operator value to ConditionSetValue
      END FOR
    END FOR

  BUILD EXISTENCE-SUFFIX RECOGNITION
    FOR EACH family IN IF_EXISTS_FAMILIES, in declared order
      operator_name := CONCAT(family, "IfExists")
      DECLARE one patternProperties entry that matches operator_name from the
        beginning through the end of the property name
      DELEGATE the matched operator value to ConditionValue
    END FOR

  PRESERVE ORDINARY OPERATORS
    RETAIN recognition of every unqualified family name in IF_EXISTS_FAMILIES
    RETAIN BinaryEquals, Bool, and Null as explicitly named Condition properties

  POSTCONDITIONS
    EVERY SET_QUALIFIERS x SET_QUALIFIED_FAMILIES combination resolves to
      ConditionSetValue
    EVERY IF_EXISTS_FAMILIES + "IfExists" combination resolves to ConditionValue
    StringEqualsIfExists resolves to ConditionValue
    ForAnyValue:StringEquals resolves to ConditionSetValue
    ForAllValues:StringEquals resolves to ConditionSetValue
    NO misspelled qualifier or suffix is introduced as an accepted alias
    BOTH identity-policy and resource-policy consumers receive the same corrected
      recognition boundary and unchanged value contracts

  ON FAILURE duplicate_or_overlapping_pattern
    REJECT the schema change until each canonical operator deterministically
      selects the intended value contract
  ON FAILURE family_missing_from_declared_matrix
    REJECT the schema change because IAMCOND-004 or IAMCOND-005 would be partial
END PROCEDURE
```

## Procedure: validate_shared_iam_condition

```text
PROCEDURE validate_shared_iam_condition(condition)
  REQUIREMENT_IDS: IAMCOND-001, IAMCOND-002, IAMCOND-003, IAMCOND-004,
                   IAMCOND-005
  VERIFICATION:
    test_iamcond_001_given_string_or_string_array_when_string_equals_if_exists_then_e3510_accepts
    test_iamcond_002_given_string_array_when_for_any_value_string_equals_then_e3510_accepts
    test_iamcond_003_given_string_array_when_for_all_values_string_equals_then_e3510_accepts
    test_iamcond_004_given_supported_comparison_family_when_correct_set_qualifier_and_array_values_then_shared_condition_accepts
    test_iamcond_005_given_non_set_comparison_family_when_if_exists_with_established_values_then_shared_condition_accepts

  PRECONDITIONS
    RECEIVE condition from a Statement.Condition reference to
      policy#/definitions/Condition

  VALIDATE CONTAINER
    IF condition is not an object
      EMIT the existing Condition type error
      TERMINATE validation of this condition value
    END IF

  VALIDATE EACH OPERATOR
    FOR EACH (operator_name, condition_key_map) IN condition, in input order
      IF operator_name is BinaryEquals, Bool, or Null
        DELEGATE to its existing explicit-property schema
      ELSE IF operator_name equals CONCAT(qualifier, family), where
              qualifier is in SET_QUALIFIERS and
              family is in SET_QUALIFIED_FAMILIES
        DELEGATE condition_key_map to ConditionSetValue
      ELSE IF operator_name equals family or CONCAT(family, "IfExists"), where
              family is in IF_EXISTS_FAMILIES
        DELEGATE condition_key_map to ConditionValue
      ELSE
        EMIT the existing additionalProperties/pattern mismatch error at
          Statement.Condition.operator_name
        CONTINUE with the next operator
      END IF

      IF delegated contract is ConditionSetValue
        REQUIRE condition_key_map to be an object
        FOR EACH (condition_key, values) IN condition_key_map
          REQUIRE values to be an array
          REQUIRE every item in values to be a string
          EMIT existing type errors at the failing condition key or item
        END FOR
      ELSE IF delegated contract is ConditionValue
        REQUIRE condition_key_map to be an object
        FOR EACH (condition_key, value) IN condition_key_map
          ACCEPT value when it is a boolean, number, or string
          ACCEPT value when it is an array whose every item is a string
          OTHERWISE EMIT the existing type error at the failing condition key
        END FOR
      END IF
    END FOR

  RETURN all emitted schema errors in validator iteration order

  ON FAILURE schema_reference_resolution
    PROPAGATE the validator's existing schema-resolution error behavior
    DO NOT translate it into operator acceptance
  ON REPEATED INVOCATION
    REVALIDATE from immutable schema and policy inputs
    DO NOT cache, persist, mutate, retry, or emit side effects
END PROCEDURE
```

## Procedure: validate_e3510_identity_policy_condition_operators

```text
PROCEDURE validate_e3510_identity_policy_condition_operators(validator, policy)
  REQUIREMENT_IDS: IAMCOND-001, IAMCOND-002, IAMCOND-003, IAMCOND-004,
                   IAMCOND-005
  VERIFICATION:
    test_iamcond_001_given_string_or_string_array_when_string_equals_if_exists_then_e3510_accepts
    test_iamcond_002_given_string_array_when_for_any_value_string_equals_then_e3510_accepts
    test_iamcond_003_given_string_array_when_for_all_values_string_equals_then_e3510_accepts
    test_iamcond_004_given_supported_comparison_family_when_correct_set_qualifier_and_array_values_then_shared_condition_accepts
    test_iamcond_005_given_non_set_comparison_family_when_if_exists_with_established_values_then_shared_condition_accepts
    test_iamcond_001_002_003_given_parallelcluster_reproduction_when_e3510_validates_both_if_exists_and_set_qualified_occurrences_then_no_condition_operator_errors

  PRECONDITIONS
    IdentityPolicy owns rule ID E3510
    IdentityPolicy has loaded policy.json as "policy" and
      policy_identity.json as "identity" into one resolver
    policy_identity.json delegates every Statement.Condition to
      policy#/definitions/Condition

  SELECT INPUT PATH
    IF validator classifies policy as a string
      EVOLVE an IAM validator with no CloudFormation functions, the identity
        schema, and the shared resolver
      ATTEMPT to decode policy as JSON
      IF JSON decoding fails
        RETURN without yielding an E3510 validation error, preserving current
          Policy.validate behavior
      END IF
    ELSE
      EVOLVE an IAM validator from the caller's CloudFormation document and
        context, the identity schema, and the shared resolver
    END IF

  VALIDATE POLICY
    FOR EACH statement selected by the identity schema
      IF Statement.Condition exists
        DELEGATE its value to validate_shared_iam_condition
      END IF
    END FOR

  CLASSIFY ERRORS
    FOR EACH error emitted by the evolved IAM validator
      IF error validator name starts with "fn_" OR equals "cfnLint"
        PRESERVE the collaborating rule already attached to the error
      ELSE
        ATTACH E3510 as the owning rule
      END IF
      YIELD error with its existing instance path, schema path, and message
    END FOR

  ACCEPTANCE TERMINAL STATE
    IF every operator is recognized and every delegated value satisfies its
       unchanged contract
      YIELD no operator-recognition or condition-value error
    END IF
    IN PARTICULAR, the ParallelCluster fixture's two StringEqualsIfExists
      occurrences, ForAnyValue:StringEquals occurrence, and
      ForAllValues:StringEquals occurrence reach this terminal state

  CONCURRENCY AND SIDE EFFECTS
    VALIDATION is synchronous and read-only
    EACH policy and each invocation is independent
    NO retry, compensation, rollback, persistence, asynchronous completion, or
      downstream event applies
END PROCEDURE
```
