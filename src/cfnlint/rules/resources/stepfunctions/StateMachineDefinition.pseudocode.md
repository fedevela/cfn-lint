# E3601 object-definition substitution awareness

Issue: `#126`

Owning runtime artifact: `StateMachineDefinition.py`

This design records the required logic without changing runtime behavior. The
provider schema remains responsible for validating `DefinitionSubstitutions`
values. E3601 only uses the presence of a declaration key to decide whether an
ASL string contains a value that CloudFormation intentionally defers.

## Procedure: `validate_state_machine_definition`

Requirement IDs: `CFNSFN-001`, `CFNSFN-002`, `CFNSFN-003`, `CFNSFN-009`

Verification obligations:

- `test_state_machine_definition_substitutions.py::test_cfnsfn_001_cfnsfn_003_declared_activity_ref_task_resource_is_accepted`
- `test_state_machine_definition_substitutions.py::test_cfnsfn_002_declared_placeholder_in_any_definition_string_bypasses_constraint[pattern_task_resource]`
- `test_state_machine_definition_substitutions.py::test_cfnsfn_002_declared_placeholder_in_any_definition_string_bypasses_constraint[enum_nested_state_type]`
- `test_state_machine_definition_substitutions.py::test_cfnsfn_002_declared_placeholder_in_any_definition_string_bypasses_constraint[format_or_equivalent_nested_choice_string]`
- `test_state_machine_definition_substitutions.py::test_cfnsfn_009_substitution_key_presence_defers_regardless_of_value[schema_valid_string]`
- `test_state_machine_definition_substitutions.py::test_cfnsfn_009_substitution_key_presence_defers_regardless_of_value[schema_valid_integer]`
- `test_state_machine_definition_substitutions.py::test_cfnsfn_009_substitution_key_presence_defers_regardless_of_value[schema_valid_boolean_true]`
- `test_state_machine_definition_substitutions.py::test_cfnsfn_009_substitution_key_presence_defers_regardless_of_value[schema_valid_falsy_zero]`
- `test_state_machine_definition_substitutions.py::test_cfnsfn_009_substitution_key_presence_defers_regardless_of_value[schema_valid_falsy_boolean_false]`
- `test_state_machine_definition_substitutions.py::test_cfnsfn_009_substitution_key_presence_defers_regardless_of_value[schema_valid_cloudformation_intrinsic]`
- `test_state_machine_definition_substitutions.py::test_cfnsfn_009_all_schema_valid_declaration_forms_are_recognized_together`
- `test_state_machine_definition_substitutions.py::test_cfnsfn_001_cfnsfn_009_complete_valid_definition_with_deferred_resource_passes`

```text
PROCEDURE validate_state_machine_definition(validator, instance)
  REQUIREMENT_IDS: CFNSFN-001, CFNSFN-002, CFNSFN-003, CFNSFN-009
  VERIFICATION: every verification obligation listed above

  PRECONDITIONS
    validator carries the current concrete template path and CloudFormation template
    instance is the value selected by E3601's Definition keyword
    the provider-schema rule independently validates DefinitionSubstitutions

  LOAD
    declared_keys := load_definition_substitution_keys(validator)

  DECIDE
    IF validator identifies instance as a string
      TRY
        definition := parse instance as JSON
        add_path_to_message := TRUE
        step_validator := evolve validator with:
          no CloudFormation functions
          E3601's ASL schema and resolver
      ON JSON_PARSE_FAILURE
        RETURN no E3601 result
        // Preserve the existing ownership of malformed Definition strings.
      END TRY
    ELSE
      definition := instance
      add_path_to_message := FALSE
      step_validator := evolve validator with E3601's ASL schema and resolver
    END IF

  VALIDATE
    FOR EACH validation_error IN step_validator.iter_errors(definition)
      filtered_error := retain_non_deferred_failure(
        validation_error,
        declared_keys,
      )

      IF filtered_error is ABSENT
        CONTINUE
        // The error was caused only by a declared, unresolved string portion.
      END IF

      IF add_path_to_message is TRUE
        recursively append the ASL path to filtered_error messages
      END IF

      IF filtered_error validator is neither a CloudFormation function validator
         nor cfnLint
        assign E3601 as filtered_error's owning rule
      END IF

      EMIT the existing cleaned representation of filtered_error
    END FOR

  RETURN
    completion after every retained error has been emitted

  REPEATED INVOCATION
    recompute declared_keys from the current owning resource
    do not mutate definition, DefinitionSubstitutions, or rule-level state
    produce the same emitted errors for the same template, path, and schema

  ON TEMPLATE_PATH_LOOKUP_FAILURE
    use an empty declared_keys set
    continue ordinary E3601 validation without deferred treatment

  ON ASL_VALIDATOR_FAILURE
    preserve the validator's established exception-to-ValidationError behavior
    do not translate an implementation failure into deferred acceptance
END PROCEDURE
```

## Procedure: `load_definition_substitution_keys`

Requirement IDs: `CFNSFN-001`, `CFNSFN-003`, `CFNSFN-009`

Verification obligations:

- `test_state_machine_definition_substitutions.py::test_cfnsfn_001_cfnsfn_003_declared_activity_ref_task_resource_is_accepted`
- `test_state_machine_definition_substitutions.py::test_cfnsfn_009_substitution_key_presence_defers_regardless_of_value[schema_valid_string]`
- `test_state_machine_definition_substitutions.py::test_cfnsfn_009_substitution_key_presence_defers_regardless_of_value[schema_valid_integer]`
- `test_state_machine_definition_substitutions.py::test_cfnsfn_009_substitution_key_presence_defers_regardless_of_value[schema_valid_boolean_true]`
- `test_state_machine_definition_substitutions.py::test_cfnsfn_009_substitution_key_presence_defers_regardless_of_value[schema_valid_falsy_zero]`
- `test_state_machine_definition_substitutions.py::test_cfnsfn_009_substitution_key_presence_defers_regardless_of_value[schema_valid_falsy_boolean_false]`
- `test_state_machine_definition_substitutions.py::test_cfnsfn_009_substitution_key_presence_defers_regardless_of_value[schema_valid_cloudformation_intrinsic]`
- `test_state_machine_definition_substitutions.py::test_cfnsfn_009_all_schema_valid_declaration_forms_are_recognized_together`
- `test_state_machine_definition_substitutions.py::test_cfnsfn_001_cfnsfn_009_complete_valid_definition_with_deferred_resource_passes`

```text
PROCEDURE load_definition_substitution_keys(validator)
  REQUIREMENT_IDS: CFNSFN-001, CFNSFN-003, CFNSFN-009
  VERIFICATION: the key-presence and complete-definition obligations listed above

  PRECONDITIONS
    validator.context.path.path identifies the concrete Definition property
    validator.cfn.template is the transformed template E3601 is validating

  LOAD
    definition_path := immutable list copied from validator.context.path.path

  VALIDATE
    IF definition_path does not end with Properties / Definition
      RETURN empty set
    END IF

  TRANSFORM
    substitutions_path := definition_path with final Definition segment replaced by
      DefinitionSubstitutions

  RECEIVE
    substitutions := traverse validator.cfn.template using substitutions_path

  DECIDE
    IF substitutions is not a mapping
      RETURN empty set
      // Provider-schema validation owns the malformed sibling value.
    END IF

  RETURN
    a new set containing every key in substitutions
    // Inspect keys only. Never resolve, coerce, or test the truthiness of values.
    // String, integer, boolean, zero, false, and intrinsic values are identical here.

  ON MISSING_PATH_OR_NON_MAPPING_ANCESTOR
    RETURN empty set
    // E3601 remains non-crashing and performs its ordinary ASL validation.
END PROCEDURE
```

## Procedure: `string_contains_declared_substitution`

Requirement IDs: `CFNSFN-001`, `CFNSFN-002`, `CFNSFN-003`, `CFNSFN-009`

Verification obligations:

- `test_state_machine_definition_substitutions.py::test_cfnsfn_001_cfnsfn_003_declared_activity_ref_task_resource_is_accepted`
- `test_state_machine_definition_substitutions.py::test_cfnsfn_002_declared_placeholder_in_any_definition_string_bypasses_constraint[pattern_task_resource]`
- `test_state_machine_definition_substitutions.py::test_cfnsfn_002_declared_placeholder_in_any_definition_string_bypasses_constraint[enum_nested_state_type]`
- `test_state_machine_definition_substitutions.py::test_cfnsfn_002_declared_placeholder_in_any_definition_string_bypasses_constraint[format_or_equivalent_nested_choice_string]`
- every `test_cfnsfn_009_*` obligation in this artifact

```text
PROCEDURE string_contains_declared_substitution(value, declared_keys)
  REQUIREMENT_IDS: CFNSFN-001, CFNSFN-002, CFNSFN-003, CFNSFN-009
  VERIFICATION: the nested-string and key-presence obligations listed above

  PRECONDITIONS
    value is the exact instance inspected by an ASL schema assertion

  DECIDE
    IF value is not a string OR declared_keys is empty
      RETURN FALSE
    END IF

  SCAN
    parse each complete ${...} placeholder token in value from left to right
    do not treat malformed or incomplete token text as a placeholder

    FOR EACH placeholder token
      referenced_keys := the substitution key names encoded by that token
      IF referenced_keys is non-empty
         AND every referenced key is present in declared_keys
        RETURN TRUE
      END IF
    END FOR

  RETURN FALSE
    // Undeclared and partially declared placeholders remain concrete to E3601.
END PROCEDURE
```

## Procedure: `retain_non_deferred_failure`

Requirement IDs: `CFNSFN-001`, `CFNSFN-002`, `CFNSFN-003`, `CFNSFN-009`

Verification obligations:

- `test_state_machine_definition_substitutions.py::test_cfnsfn_001_cfnsfn_003_declared_activity_ref_task_resource_is_accepted`
- `test_state_machine_definition_substitutions.py::test_cfnsfn_002_declared_placeholder_in_any_definition_string_bypasses_constraint[pattern_task_resource]`
- `test_state_machine_definition_substitutions.py::test_cfnsfn_002_declared_placeholder_in_any_definition_string_bypasses_constraint[enum_nested_state_type]`
- `test_state_machine_definition_substitutions.py::test_cfnsfn_002_declared_placeholder_in_any_definition_string_bypasses_constraint[format_or_equivalent_nested_choice_string]`
- every `test_cfnsfn_009_*` obligation in this artifact

```text
PROCEDURE retain_non_deferred_failure(error, declared_keys)
  REQUIREMENT_IDS: CFNSFN-001, CFNSFN-002, CFNSFN-003, CFNSFN-009
  VERIFICATION: the acceptance and constraint-bypass obligations listed above

  DECIDE DIRECT FAILURE
    IF string_contains_declared_substitution(error.instance, declared_keys)
      RETURN ABSENT
      // Covers pattern, enum, const, format, length, type-alternative, and other
      // concrete assertions whose failing instance is the deferred string itself.
    END IF

  DECIDE COMPOSITE FAILURE
    IF error.context is empty
      RETURN error unchanged
    END IF

    retained_context := empty list
    FOR EACH child_error IN error.context in original order
      retained_child := retain_non_deferred_failure(child_error, declared_keys)
      IF retained_child is PRESENT
        append retained_child to retained_context
      END IF
    END FOR

    IF retained_context is empty
      RETURN ABSENT
      // A combinator failure caused exclusively by deferred string leaves vanishes.
    END IF

  TRANSFORM
    copy error and replace only its context with retained_context

  RETURN copied error
    // Structural failures such as required properties, additional properties,
    // invalid containers, and unrelated concrete values remain observable.

  ORDERING
    run ordinary ASL validation before this procedure
    never replace a placeholder with a wildcard before evaluating if/then guards
    // In particular, an unresolved Type must not satisfy every state-type guard.
END PROCEDURE
```

## Control-flow invariants

- E3601 reads `DefinitionSubstitutions` but never validates, resolves, mutates, or
  persists it; the CloudFormation provider schema retains that responsibility.
- Declaration recognition is scoped to the concrete owning state machine obtained
  from `validator.context.path.path`. Keys from another resource never defer a
  placeholder in this definition.
- Every string leaf in the object-valued `Definition` is eligible, regardless of
  nesting depth. Recursive schema validation supplies the leaf and its ASL path.
- Ordinary ASL validation happens first. Deferred-error filtering happens second,
  followed by the existing message-path decoration, rule assignment, and cleaning.
- Missing or malformed declarations grant no exemption. Unrelated ASL failures are
  emitted with their existing path, schema path, rule ownership, and ordering.
- Validation is synchronous and read-only. There is no retry, persistence,
  compensation, rollback, queue, scheduled work, or asynchronous completion path.

