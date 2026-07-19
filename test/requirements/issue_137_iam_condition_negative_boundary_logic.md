# Issue 137 IAM Condition Negative-Boundary Logic

This artifact specifies the deterministic rejection and string-context logic for
the shared IAM Condition schema used by E3510. It changes no runtime behavior by
itself and complements the positive operator procedures in
`issue_136_iam_condition_operator_logic.md`.

## Exact operator vocabulary

`SET_QUALIFIERS` contains exactly `ForAnyValue:` and `ForAllValues:`. Each
qualifier is case-sensitive and uses singular `Value`.

`SET_QUALIFIED_FAMILIES` contains the same 20 canonical comparison names as the
Issue 136 logic artifact. A set-qualified operator is recognized only when its
complete property name equals one `SET_QUALIFIERS x SET_QUALIFIED_FAMILIES`
combination. There are no aliases for unknown names, `ForAnyValues:`, misspelled
families, whitespace, punctuation, or other extraneous characters.

## Procedure: reject_unrecognized_condition_operator

```text
PROCEDURE reject_unrecognized_condition_operator(condition, policy_path)
  REQUIREMENT_IDS: IAMCOND-009
  VERIFICATION:
    test_iamcond_009_given_unknown_unsupported_or_malformed_operator_when_e3510_validates_then_error_path_ends_at_that_operator
    test_iamcond_009_given_malformed_operator_alongside_corrected_operator_when_e3510_validates_then_malformed_error_remains_and_corrected_operator_adds_no_error

  PRECONDITIONS
    RECEIVE condition from Statement.Condition through
      policy_identity.json#/definitions/Statement/properties/Condition
    REQUIRE policy.json#/definitions/Condition to retain
      additionalProperties as false
    REQUIRE every patternProperties expression to match its canonical operator
      name from the first character through the last character
    PRESERVE the explicit BinaryEquals, Bool, and Null properties

  VALIDATE EACH OPERATOR INDEPENDENTLY
    FOR EACH (operator_name, condition_key_map) IN condition, in input order
      matched_contracts := EMPTY

      IF operator_name is exactly BinaryEquals, Bool, or Null
        ADD that explicit property's existing contract to matched_contracts
      END IF

      FOR EACH anchored_pattern IN Condition.patternProperties, in schema order
        IF anchored_pattern matches the complete operator_name
          ADD anchored_pattern's referenced value contract to matched_contracts
        END IF
      END FOR

      DECIDE
        IF matched_contracts is EMPTY
          CLASSIFY operator_name as an additional property
          EMIT the existing pattern-mismatch validation error
          SET error.path to CONCAT(policy_path, ["Condition", operator_name])
          CONTINUE with the next operator without validating this operator's
            condition_key_map against a recognized value contract
        ELSE
          FOR EACH matched_contract IN matched_contracts, in schema order
            DELEGATE condition_key_map to matched_contract
            PRESERVE every resulting nested path and error
          END FOR
        END IF
      END DECIDE
    END FOR

  POSTCONDITIONS
    UnknownOperator is rejected
    ForAnyValues:StringEquals is rejected
    ForAnyValue:StringEqual is rejected
    Any leading, trailing, or embedded extraneous character prevents a match
    Each rejection path terminates at the exact malformed operator property
    A rejected operator does not halt, erase, or alter validation of sibling
      operators
    A correctly spelled sibling operator contributes no error when its value
      satisfies the delegated contract

  RETURN all emitted errors in validator iteration order

  ON FAILURE duplicate_or_overlapping_recognition
    PRESERVE every emitted delegated error; do not use one match to suppress
      another match
  ON REPEATED INVOCATION
    REEVALUATE immutable schema and policy inputs
    DO NOT cache, mutate, persist, retry, or emit side effects
END PROCEDURE
```

## Procedure: validate_set_qualified_condition_values

```text
PROCEDURE validate_set_qualified_condition_values(
  operator_name,
  condition_key_map,
  policy_path,
  validation_context
)
  REQUIREMENT_IDS: IAMCOND-010
  VERIFICATION:
    test_iamcond_010_given_set_qualified_condition_key_maps_to_non_array_when_e3510_validates_then_value_is_rejected_at_operator_and_key_path
    test_iamcond_010_given_set_qualified_array_contains_non_string_compatible_elements_when_e3510_validates_then_each_is_rejected_at_policy_relative_array_path
    test_iamcond_010_given_each_set_condition_key_has_literal_strings_and_supported_cfn_string_expressions_when_object_policy_with_functions_is_validated_then_no_type_or_operator_errors

  PRECONDITIONS
    REQUIRE operator_name to equal CONCAT(qualifier, family), where qualifier is
      in SET_QUALIFIERS and family is in SET_QUALIFIED_FAMILIES
    RECEIVE condition_key_map after the operator pattern delegates to
      policy.json#/definitions/ConditionSetValue
    DEFINE operator_path as CONCAT(policy_path, ["Condition", operator_name])

  VALIDATE CONDITION-KEY CONTAINER
    IF condition_key_map is not an object
      EMIT the existing object type error at operator_path
      TERMINATE validation of this operator value
    END IF

  VALIDATE EACH CONDITION KEY
    FOR EACH (condition_key, values) IN condition_key_map, in input order
      key_path := CONCAT(operator_path, [condition_key])

      IF values is not an array
        EMIT the existing array type error at key_path
        CONTINUE with the next condition_key
      END IF

      FOR EACH (index, item) IN values, in index order
        item_path := CONCAT(key_path, [index])

        IF item is a literal string
          ACCEPT item
          CONTINUE with the next item
        END IF

        IF item is a singleton object whose property name is in
           validation_context.functions
          DELEGATE item to the existing CloudFormation FunctionFilter while
            retaining the ConditionSetValue item schema {type: "string"}
          DELEGATE the function payload and any resolved result to its existing
            function validator
          IF function validation establishes compatibility with the string
             context and emits no function error
            ACCEPT item
          ELSE
            PROPAGATE each function validation error with item_path as its
              policy-relative prefix and preserve the collaborating function rule
          END IF
          CONTINUE with the next item
        END IF

        EMIT the existing strict string type error at item_path
      END FOR
    END FOR

  POSTCONDITIONS
    Scalar strings, booleans, numbers, objects, and null condition-key values are
      rejected at their key_path because none is an array
    Within arrays, booleans, numbers, null, and unsupported objects are rejected
      independently at their item_path
    Literal strings are accepted
    Supported Ref and Fn::Sub expressions are accepted only when function
      support is enabled and they satisfy the existing string-context semantics
    Validation of one key or item does not suppress validation of later keys or
      items

  RETURN all emitted errors in validator iteration order

  ON FAILURE schema_reference_resolution
    PROPAGATE the existing schema-resolution failure
    DO NOT widen the value contract to recover
  ON FAILURE unsupported_function_object
    TREAT the object as a non-string-compatible item and preserve item_path
  ON REPEATED INVOCATION
    REVALIDATE every key and item from immutable inputs
    DO NOT cache, mutate, persist, retry, compensate, or roll back
END PROCEDURE
```

## Procedure: validate_e3510_condition_negative_boundary

```text
PROCEDURE validate_e3510_condition_negative_boundary(validator, policy)
  REQUIREMENT_IDS: IAMCOND-009, IAMCOND-010
  VERIFICATION:
    test_iamcond_009_given_unknown_unsupported_or_malformed_operator_when_e3510_validates_then_error_path_ends_at_that_operator
    test_iamcond_009_given_malformed_operator_alongside_corrected_operator_when_e3510_validates_then_malformed_error_remains_and_corrected_operator_adds_no_error
    test_iamcond_010_given_set_qualified_condition_key_maps_to_non_array_when_e3510_validates_then_value_is_rejected_at_operator_and_key_path
    test_iamcond_010_given_set_qualified_array_contains_non_string_compatible_elements_when_e3510_validates_then_each_is_rejected_at_policy_relative_array_path
    test_iamcond_010_given_each_set_condition_key_has_literal_strings_and_supported_cfn_string_expressions_when_object_policy_with_functions_is_validated_then_no_type_or_operator_errors

  PRECONDITIONS
    IdentityPolicy owns rule ID E3510
    Policy.__init__ has loaded policy.json and policy_identity.json into the
      resolver store
    policy_identity.json delegates Statement.Condition to the shared Condition
      definition

  SELECT VALIDATION CONTEXT
    IF validator classifies policy as a string
      EVOLVE an IAM validator with CloudFormation functions disabled
      ATTEMPT to decode policy as JSON
      IF decoding fails
        RETURN without yielding an E3510 validation error, preserving current
          Policy.validate behavior
      END IF
    ELSE
      EVOLVE an IAM validator with the caller's CloudFormation document,
        context, supported-function set, shared resolver, and identity schema
    END IF

  VALIDATE POLICY
    FOR EACH Statement selected by policy_identity.json, in validator order
      IF Statement.Condition exists
        DELEGATE operator recognition to
          reject_unrecognized_condition_operator
        FOR EACH exactly recognized set-qualified operator
          DELEGATE its condition-key map to
            validate_set_qualified_condition_values
        END FOR
      END IF
    END FOR

  CLASSIFY AND YIELD ERRORS
    FOR EACH error emitted by the evolved IAM validator
      IF error.validator starts with "fn_" OR equals "cfnLint"
        PRESERVE the collaborating rule already attached to error
      ELSE
        ATTACH E3510 as the owning rule
      END IF
      YIELD error with its existing message, instance path, and schema path
    END FOR

  TERMINAL STATES
    MALFORMED_OPERATOR:
      YIELD an E3510 error ending at Statement.Condition.operator_name
    INVALID_SET_CONTAINER:
      YIELD an E3510 error ending at
        Statement.Condition.operator_name.condition_key
    INVALID_SET_ITEM:
      YIELD one E3510 error per invalid item ending at
        Statement.Condition.operator_name.condition_key.index
    VALID_SET_VALUES:
      YIELD no type or operator error when every key maps to an array and every
        item is a literal string or a supported string-context expression

  ORDERING, CONCURRENCY, AND SIDE EFFECTS
    VALIDATION is synchronous, read-only, and invocation-local
    SIBLING operators, condition keys, and array items are independently visited
    ERRORS remain in validator traversal order
    NO persistence, transaction, queue, asynchronous completion, retry,
      compensation, rollback, notification, or downstream event applies
END PROCEDURE
```

## Traceability and implementation boundary

The bidirectional requirement, verification, schema-locus, and procedure links
are maintained in
`test/requirements/issue_137_iam_condition_negative_boundary_verification.json`.
Runtime ownership remains confined to the existing shared schema, validator,
and E3510 entry point; this phase introduces no production-source change.
