# E3601 object-definition substitution awareness

Issues: `#126`, `#127`, `#128`, `#129`

Owning runtime artifact: `StateMachineDefinition.py`

This design records the logic embodied by the runtime implementation. The provider
schema remains responsible for validating `DefinitionSubstitutions` values. E3601
only uses the presence of a declaration key to decide whether an ASL string
contains a value that CloudFormation intentionally defers.

Issue #127 tightens that decision: the declaration set is loaded only from the
current state-machine resource, and a string is deferred only when at least one
supported substitution token is present and every key referenced by every token
is declared in that owning set.

Issue #128 preserves the boundary around that narrow deferral. The complete ASL
schema still runs before filtering, and only a failure whose own failing string
is a fully declared substitution value may disappear. Concrete Task resources,
structural and state-type failures, transition and termination relationships, and
ordinary object definitions remain subject to their established E3601 findings,
paths, ordering, and acceptance behavior.

Issue #129 preserves the boundary between rule owners. Provider-schema validation
continues to own the `DefinitionSubstitutions` container and values, and its
findings are accumulated independently of E3601's read-only use of declaration
keys. E3601 remains registered for object-valued `Definition` only; the provider's
presence of `DefinitionString` does not reactivate that intentionally disabled
keyword surface.

## Procedure: `validate_state_machine_definition`

Requirement IDs: `CFNSFN-001`, `CFNSFN-002`, `CFNSFN-003`, `CFNSFN-004`,
`CFNSFN-005`, `CFNSFN-006`, `CFNSFN-007`, `CFNSFN-008`, `CFNSFN-009`,
`CFNSFN-011`, `CFNSFN-012`

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
- `test_state_machine_definition_substitution_ownership.py::test_cfnsfn_004_when_task_resource_placeholder_is_undeclared_e3601_pattern_finding_remains`
- `test_state_machine_definition_substitution_ownership.py::test_cfnsfn_005_when_only_first_owner_declares_shared_placeholder_e3601_reports_second_only`
- `test_state_machine_definition_substitution_ownership.py::test_cfnsfn_011_when_embedded_placeholders_are_all_declared_e3601_defers_complete_string`
- `test_state_machine_definition_substitution_ownership.py::test_cfnsfn_011_when_comma_delimited_keys_are_all_declared_e3601_defers_complete_form`
- `test_state_machine_definition_substitution_ownership.py::test_cfnsfn_004_cfnsfn_011_when_embedded_placeholder_is_partially_declared_e3601_pattern_finding_remains`
- `test_state_machine_definition_substitution_ownership.py::test_cfnsfn_004_cfnsfn_011_when_comma_delimited_keys_are_partially_declared_e3601_pattern_finding_remains`
- `test_state_machine_definition_validation_continuity.py::test_cfnsfn_006_when_task_resource_is_concrete_and_invalid_e3601_reports_pattern_at_resource`
- `test_state_machine_definition_validation_continuity.py::test_cfnsfn_007_when_substitution_exists_and_task_resource_is_missing_e3601_reports_required_at_state`
- `test_state_machine_definition_validation_continuity.py::test_cfnsfn_007_when_substitution_exists_and_state_has_unsupported_field_e3601_reports_additional_properties_at_state`
- `test_state_machine_definition_validation_continuity.py::test_cfnsfn_007_when_substitution_exists_and_state_type_is_invalid_e3601_reports_enum_at_type`
- `test_state_machine_definition_validation_continuity.py::test_cfnsfn_008_when_substitution_exists_and_task_has_neither_next_nor_end_e3601_reports_required_xor_at_state`
- `test_state_machine_definition_validation_continuity.py::test_cfnsfn_008_when_substitution_exists_and_task_has_both_next_and_end_e3601_reports_required_xor_at_each_property`
- `test_state_machine_definition_validation_continuity.py::test_cfnsfn_008_when_substitution_exists_and_task_next_is_empty_e3601_reports_pattern_at_next`
- `test_state_machine_definition_validation_continuity.py::test_cfnsfn_012_when_object_definition_has_no_placeholders_and_is_valid_e3601_acceptance_is_unchanged`
- `test_state_machine_definition_validation_continuity.py::test_cfnsfn_012_when_object_definition_has_no_placeholders_and_resource_is_invalid_e3601_pattern_and_path_are_unchanged`

```text
PROCEDURE validate_state_machine_definition(validator, instance)
  REQUIREMENT_IDS: CFNSFN-001, CFNSFN-002, CFNSFN-003, CFNSFN-004,
    CFNSFN-005, CFNSFN-006, CFNSFN-007, CFNSFN-008, CFNSFN-009,
    CFNSFN-011, CFNSFN-012
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
      // Run the unchanged, complete ASL schema before making any substitution
      // decision. Do not replace strings or disable schema branches in advance.
      filtered_error := retain_non_deferred_failure(
        validation_error,
        declared_keys,
      )

      IF filtered_error is ABSENT
        CONTINUE
        // Every failing leaf in this error tree was the exact string value of a
        // fully declared substitution. No unrelated failure is present.
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
    // A valid object definition with no deferred failing strings emits nothing.
    // An invalid object definition with no deferred failing strings emits the
    // same cleaned errors, paths, schema paths, rule ownership, and order as the
    // ordinary E3601 pipeline.

  REPEATED INVOCATION
    recompute declared_keys from the current owning resource
    discard the prior invocation's declared_keys before validating another resource
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

Requirement IDs: `CFNSFN-001`, `CFNSFN-003`, `CFNSFN-004`, `CFNSFN-005`,
`CFNSFN-006`, `CFNSFN-007`, `CFNSFN-008`, `CFNSFN-009`, `CFNSFN-011`,
`CFNSFN-012`

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
- `test_state_machine_definition_substitution_ownership.py::test_cfnsfn_004_when_task_resource_placeholder_is_undeclared_e3601_pattern_finding_remains`
- `test_state_machine_definition_substitution_ownership.py::test_cfnsfn_005_when_only_first_owner_declares_shared_placeholder_e3601_reports_second_only`
- `test_state_machine_definition_substitution_ownership.py::test_cfnsfn_011_when_embedded_placeholders_are_all_declared_e3601_defers_complete_string`
- `test_state_machine_definition_substitution_ownership.py::test_cfnsfn_011_when_comma_delimited_keys_are_all_declared_e3601_defers_complete_form`
- `test_state_machine_definition_substitution_ownership.py::test_cfnsfn_004_cfnsfn_011_when_embedded_placeholder_is_partially_declared_e3601_pattern_finding_remains`
- `test_state_machine_definition_substitution_ownership.py::test_cfnsfn_004_cfnsfn_011_when_comma_delimited_keys_are_partially_declared_e3601_pattern_finding_remains`
- every `test_state_machine_definition_validation_continuity.py::*` obligation
  listed under `validate_state_machine_definition`

```text
PROCEDURE load_definition_substitution_keys(validator)
  REQUIREMENT_IDS: CFNSFN-001, CFNSFN-003, CFNSFN-004, CFNSFN-005,
    CFNSFN-006, CFNSFN-007, CFNSFN-008, CFNSFN-009, CFNSFN-011,
    CFNSFN-012
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
    // Preserve every preceding segment, including the concrete Resources logical ID.

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
    // Do not merge, cache, or consult substitutions from any other resource path.

  ON MISSING_PATH_OR_NON_MAPPING_ANCESTOR
    RETURN empty set
    // E3601 remains non-crashing and performs its ordinary ASL validation.
END PROCEDURE
```

## Procedure: `string_contains_declared_substitution`

Requirement IDs: `CFNSFN-001`, `CFNSFN-002`, `CFNSFN-003`, `CFNSFN-004`,
`CFNSFN-005`, `CFNSFN-006`, `CFNSFN-007`, `CFNSFN-008`, `CFNSFN-009`,
`CFNSFN-011`, `CFNSFN-012`

Verification obligations:

- `test_state_machine_definition_substitutions.py::test_cfnsfn_001_cfnsfn_003_declared_activity_ref_task_resource_is_accepted`
- `test_state_machine_definition_substitutions.py::test_cfnsfn_002_declared_placeholder_in_any_definition_string_bypasses_constraint[pattern_task_resource]`
- `test_state_machine_definition_substitutions.py::test_cfnsfn_002_declared_placeholder_in_any_definition_string_bypasses_constraint[enum_nested_state_type]`
- `test_state_machine_definition_substitutions.py::test_cfnsfn_002_declared_placeholder_in_any_definition_string_bypasses_constraint[format_or_equivalent_nested_choice_string]`
- every `test_cfnsfn_009_*` obligation in this artifact
- `test_state_machine_definition_substitution_ownership.py::test_cfnsfn_004_when_task_resource_placeholder_is_undeclared_e3601_pattern_finding_remains`
- `test_state_machine_definition_substitution_ownership.py::test_cfnsfn_005_when_only_first_owner_declares_shared_placeholder_e3601_reports_second_only`
- `test_state_machine_definition_substitution_ownership.py::test_cfnsfn_011_when_embedded_placeholders_are_all_declared_e3601_defers_complete_string`
- `test_state_machine_definition_substitution_ownership.py::test_cfnsfn_011_when_comma_delimited_keys_are_all_declared_e3601_defers_complete_form`
- `test_state_machine_definition_substitution_ownership.py::test_cfnsfn_004_cfnsfn_011_when_embedded_placeholder_is_partially_declared_e3601_pattern_finding_remains`
- `test_state_machine_definition_substitution_ownership.py::test_cfnsfn_004_cfnsfn_011_when_comma_delimited_keys_are_partially_declared_e3601_pattern_finding_remains`
- every `test_state_machine_definition_validation_continuity.py::*` obligation
  listed under `validate_state_machine_definition`

```text
PROCEDURE string_contains_declared_substitution(value, declared_keys)
  REQUIREMENT_IDS: CFNSFN-001, CFNSFN-002, CFNSFN-003, CFNSFN-004,
    CFNSFN-005, CFNSFN-006, CFNSFN-007, CFNSFN-008, CFNSFN-009,
    CFNSFN-011, CFNSFN-012
  VERIFICATION: the nested-string and key-presence obligations listed above

  PRECONDITIONS
    value is the exact instance inspected by an ASL schema assertion

  DECIDE
    IF value is not a string OR declared_keys is empty
      RETURN FALSE
    END IF

  SCAN
    token_bodies := every complete non-literal ${...} placeholder body in value,
      parsed from left to right with the shared REGEX_SUB_PARAMETERS grammar
    do not treat malformed or incomplete token text as a placeholder
    do not treat the escaped ${!...} literal form as a substitution token

    IF token_bodies is empty
      RETURN FALSE
    END IF

    referenced_keys := empty ordered list
    FOR EACH token_body IN token_bodies
      token_keys := split token_body at every comma, preserving key text exactly
      IF token_keys is empty OR any token_key is empty
        RETURN FALSE
        // An unsupported empty component cannot authorize the failing string.
      END IF
      append every token_key to referenced_keys in source order
    END FOR

  DECIDE
    IF every referenced_key in referenced_keys is present in declared_keys
      RETURN TRUE
    END IF

  RETURN FALSE
    // One missing key in any standalone, embedded, or comma-delimited token keeps
    // the complete failing string concrete and observable to E3601.
END PROCEDURE
```

## Procedure: `retain_non_deferred_failure`

Requirement IDs: `CFNSFN-001`, `CFNSFN-002`, `CFNSFN-003`, `CFNSFN-004`,
`CFNSFN-005`, `CFNSFN-006`, `CFNSFN-007`, `CFNSFN-008`, `CFNSFN-009`,
`CFNSFN-011`, `CFNSFN-012`

Verification obligations:

- `test_state_machine_definition_substitutions.py::test_cfnsfn_001_cfnsfn_003_declared_activity_ref_task_resource_is_accepted`
- `test_state_machine_definition_substitutions.py::test_cfnsfn_002_declared_placeholder_in_any_definition_string_bypasses_constraint[pattern_task_resource]`
- `test_state_machine_definition_substitutions.py::test_cfnsfn_002_declared_placeholder_in_any_definition_string_bypasses_constraint[enum_nested_state_type]`
- `test_state_machine_definition_substitutions.py::test_cfnsfn_002_declared_placeholder_in_any_definition_string_bypasses_constraint[format_or_equivalent_nested_choice_string]`
- every `test_cfnsfn_009_*` obligation in this artifact
- `test_state_machine_definition_substitution_ownership.py::test_cfnsfn_004_when_task_resource_placeholder_is_undeclared_e3601_pattern_finding_remains`
- `test_state_machine_definition_substitution_ownership.py::test_cfnsfn_005_when_only_first_owner_declares_shared_placeholder_e3601_reports_second_only`
- `test_state_machine_definition_substitution_ownership.py::test_cfnsfn_011_when_embedded_placeholders_are_all_declared_e3601_defers_complete_string`
- `test_state_machine_definition_substitution_ownership.py::test_cfnsfn_011_when_comma_delimited_keys_are_all_declared_e3601_defers_complete_form`
- `test_state_machine_definition_substitution_ownership.py::test_cfnsfn_004_cfnsfn_011_when_embedded_placeholder_is_partially_declared_e3601_pattern_finding_remains`
- `test_state_machine_definition_substitution_ownership.py::test_cfnsfn_004_cfnsfn_011_when_comma_delimited_keys_are_partially_declared_e3601_pattern_finding_remains`
- `test_state_machine_definition_validation_continuity.py::test_cfnsfn_006_when_task_resource_is_concrete_and_invalid_e3601_reports_pattern_at_resource`
- `test_state_machine_definition_validation_continuity.py::test_cfnsfn_007_when_substitution_exists_and_task_resource_is_missing_e3601_reports_required_at_state`
- `test_state_machine_definition_validation_continuity.py::test_cfnsfn_007_when_substitution_exists_and_state_has_unsupported_field_e3601_reports_additional_properties_at_state`
- `test_state_machine_definition_validation_continuity.py::test_cfnsfn_007_when_substitution_exists_and_state_type_is_invalid_e3601_reports_enum_at_type`
- `test_state_machine_definition_validation_continuity.py::test_cfnsfn_008_when_substitution_exists_and_task_has_neither_next_nor_end_e3601_reports_required_xor_at_state`
- `test_state_machine_definition_validation_continuity.py::test_cfnsfn_008_when_substitution_exists_and_task_has_both_next_and_end_e3601_reports_required_xor_at_each_property`
- `test_state_machine_definition_validation_continuity.py::test_cfnsfn_008_when_substitution_exists_and_task_next_is_empty_e3601_reports_pattern_at_next`
- `test_state_machine_definition_validation_continuity.py::test_cfnsfn_012_when_object_definition_has_no_placeholders_and_is_valid_e3601_acceptance_is_unchanged`
- `test_state_machine_definition_validation_continuity.py::test_cfnsfn_012_when_object_definition_has_no_placeholders_and_resource_is_invalid_e3601_pattern_and_path_are_unchanged`

```text
PROCEDURE retain_non_deferred_failure(error, declared_keys)
  REQUIREMENT_IDS: CFNSFN-001, CFNSFN-002, CFNSFN-003, CFNSFN-004,
    CFNSFN-005, CFNSFN-006, CFNSFN-007, CFNSFN-008, CFNSFN-009,
    CFNSFN-011, CFNSFN-012
  VERIFICATION: every verification obligation listed above

  PRECONDITIONS
    error is one complete, fresh error tree emitted by ordinary ASL validation
    declared_keys belongs only to the state machine whose Definition produced error
    no Definition value has been substituted, normalized, or mutated

  DECIDE DIRECT FAILURE
    IF string_contains_declared_substitution(error.instance, declared_keys)
      RETURN ABSENT
      // Covers pattern, enum, const, format, length, type-alternative, and other
      // concrete assertions whose failing instance is the deferred string itself.
    END IF

    IF error.instance is a concrete string with no supported placeholder
      RETURN error unchanged
      // Preserve Resource and Next pattern failures, Type enum failures, and every
      // other concrete string constraint at its original observable path.
    END IF

    IF error.instance is an object, array, number, boolean, or null
      do not authorize deferral from any declared placeholder nested elsewhere
      // Required, additionalProperties, requiredXor, and container/type failures
      // are decided from this exact structural instance, not from sibling fields.
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
    preserve validator, message, instance, path, schema path, and rule metadata
    set each retained child's parent to the copied error

  RETURN copied error
    // Structural failures such as required properties, additional properties,
    // invalid containers, and unrelated concrete values remain observable.

  ORDERING
    run ordinary ASL validation before this procedure
    never replace a placeholder with a wildcard before evaluating if/then guards
    // In particular, an unresolved Type must not satisfy every state-type guard.
    retain original child order when deferred and non-deferred failures coexist

  CONTINUITY CASES
    concrete invalid Task Resource -> retain pattern at States / state / Resource
    missing Task Resource -> retain required at States / state
    unsupported state field -> retain additionalProperties at States / state / field
    concrete invalid state Type -> retain enum at States / state / Type
    neither Next nor End -> retain requiredXor at States / state
    both Next and End -> retain requiredXor at each property path
    empty concrete Next -> retain pattern at States / state / Next
    valid object Definition with no failing placeholder -> return no errors
    invalid object Definition with no failing placeholder -> retain errors unchanged

  REPEATED INVOCATION
    do not mutate error trees returned by prior invocations
    return the original error object when neither it nor its descendants change
    copy only a composite node whose child context is partially retained

  ON UNRELATED OR UNCLASSIFIED ASL FAILURE
    RETURN the failure unchanged
    // Deferral is an explicit narrow exemption, never a default recovery path.
END PROCEDURE
```

## Procedure: `preserve_state_machine_validation_surface_boundaries`

Requirement IDs: `CFNSFN-010`, `CFNSFN-013`

Verification obligations:

- `test_state_machine_validation_surface_boundaries.py::test_cfnsfn_010_when_definition_substitutions_map_has_invalid_shape_property_schema_finding_remains_observable`
- `test_state_machine_validation_surface_boundaries.py::test_cfnsfn_010_when_corresponding_placeholder_has_invalid_substitution_value_property_schema_finding_remains_observable`
- `test_state_machine_validation_surface_boundaries.py::test_cfnsfn_010_when_substitution_value_is_schema_valid_property_schema_accepts_while_e3601_defers_placeholder`
- `test_state_machine_validation_surface_boundaries.py::test_cfnsfn_013_when_definition_string_contains_invalid_asl_lint_introduces_no_e3601_finding`
- `test_state_machine_validation_surface_boundaries.py::test_cfnsfn_013_when_provider_schema_has_both_definition_interfaces_e3601_registers_only_object_definition`

```text
PROCEDURE preserve_state_machine_validation_surface_boundaries(
  template,
  provider_schema,
  enabled_rules,
)
  REQUIREMENT_IDS: CFNSFN-010, CFNSFN-013
  VERIFICATION: every verification obligation listed above

  PRECONDITIONS
    provider_schema is the regional AWS::StepFunctions::StateMachine schema
    provider_schema exposes Definition, DefinitionString, and
      DefinitionSubstitutions as separate properties
    enabled_rules contains the ordinary provider-property rule and may contain E3601
    findings is a per-lint-run collection; no rule may delete another rule's finding

  LOAD / RECEIVE
    FOR EACH AWS::StepFunctions::StateMachine resource IN template
      properties := resource.Properties, or an empty mapping when absent

  DELEGATE PROVIDER-SCHEMA OWNERSHIP
    provider_findings := validate properties against provider_schema
    // Properties validation dispatches each schema keyword to its existing child
    // rule, including E3012 for type failures and E3017 for anyOf failures.

    FOR EACH provider_finding IN provider_findings
      append provider_finding to findings with its original rule and property path
      // Never pass provider findings through E3601's deferred-error filter.
    END FOR

  DECIDE DEFINITION-SUBSTITUTION SHAPE AND VALUES
    IF DefinitionSubstitutions is absent
      preserve zero provider findings for that absent optional property
    ELSE IF DefinitionSubstitutions is not an object
      preserve the provider type finding at DefinitionSubstitutions
      // E3601's declaration-key reader receives no keys from a non-mapping value.
    ELSE
      FOR EACH substitution_value IN DefinitionSubstitutions
        IF substitution_value is a schema-valid string, integer, or boolean
          preserve provider-schema acceptance
          // This includes zero and false; acceptance is based on type, not truth.
        ELSE IF substitution_value is a supported CloudFormation intrinsic
          preserve the provider validator's established intrinsic-function handling
        ELSE
          preserve every provider type or anyOf finding at the substitution value
        END IF
      END FOR
    END IF

  DELEGATE E3601 OWNERSHIP
    e3601_keywords := register_e3601_definition_surface(provider_schema)

    IF E3601 is enabled AND properties.Definition is selected by e3601_keywords
      e3601_findings := validate_state_machine_definition(
        validator scoped to this resource's Definition path,
        properties.Definition,
      )
      append every e3601_finding to findings
      // E3601 may use sibling declaration-key presence to defer an exact failing
      // ASL string. It does not validate substitution values and cannot consume,
      // translate, replace, or suppress provider_findings.
    END IF

    IF DefinitionString is present
      do not invoke E3601 for DefinitionString
      do not parse DefinitionString with the E3601 ASL schema
      do not emit an E3601 finding from DefinitionString
      // Provider-schema validation still owns DefinitionString's property schema.
    END IF

  RETURN
    findings containing the independent union of all retained provider findings
      and only the E3601 findings produced for object-valued Definition invocations

  ORDERING / CONCURRENCY
    provider validation and E3601 selection are independent validation branches
      within the full-template rule traversal
    their dispatch order does not alter either branch's inputs or findings
    merge findings without shared mutable validation state or cross-rule filtering

  REPEATED INVOCATION
    recreate all per-run finding collections and per-resource declaration-key sets
    preserve identical owner, path, and result for identical input and rule config

  ON PROVIDER-SCHEMA REJECTION
    retain the provider finding and continue every independently enabled rule
    do not convert a property-schema rejection into an E3601 failure or acceptance

  ON E3601 DEFERRED PLACEHOLDER
    suppress only the qualifying ASL failure selected by
      retain_non_deferred_failure
    retain all previously accumulated provider findings unchanged

  ON RULE-LOCAL FAILURE
    preserve the lint engine's established rule-failure propagation
    do not treat one owner's implementation failure as another owner's acceptance
END PROCEDURE
```

## Procedure: `register_e3601_definition_surface`

Requirement IDs: `CFNSFN-013`

Verification obligations:

- `test_state_machine_validation_surface_boundaries.py::test_cfnsfn_013_when_definition_string_contains_invalid_asl_lint_introduces_no_e3601_finding`
- `test_state_machine_validation_surface_boundaries.py::test_cfnsfn_013_when_provider_schema_has_both_definition_interfaces_e3601_registers_only_object_definition`

```text
PROCEDURE register_e3601_definition_surface(provider_schema)
  REQUIREMENT_IDS: CFNSFN-013
  VERIFICATION: every verification obligation listed above

  PRECONDITIONS
    E3601 is being initialized before keyword-based rule dispatch
    provider_schema may expose both Definition and DefinitionString

  LOAD
    active_keyword :=
      Resources/AWS::StepFunctions::StateMachine/Properties/Definition
    intentionally_disabled_keyword :=
      Resources/AWS::StepFunctions::StateMachine/Properties/DefinitionString

  REGISTER
    register active_keyword as E3601's sole keyword
    // The explicit rule contract, rather than provider-property discovery, controls
    // keyword dispatch.

  INSPECT COMPATIBILITY WITHOUT BROADENING
    confirm provider_schema exposes Definition for the active interface
    IF provider_schema exposes DefinitionString
      do not register intentionally_disabled_keyword
      // Schema availability is not authority to broaden a rule's keyword surface.
    END IF

  RETURN
    ordered keyword collection containing exactly active_keyword

  DELEGATION
    keyword dispatch may invoke validate_state_machine_definition only when the
      current concrete template path matches active_keyword
    DefinitionString remains outside E3601 regardless of its contents

  REPEATED INVOCATION
    return the same one-element keyword collection without mutating provider_schema
    do not infer or auto-register newly visible provider properties

  ON MISSING OR CHANGED PROVIDER PROPERTY
    preserve the explicit one-keyword E3601 contract
    surface schema compatibility changes through their owning update process
    never fall back to DefinitionString
END PROCEDURE
```

## Control-flow invariants

- E3601 reads `DefinitionSubstitutions` but never validates, resolves, mutates, or
  persists it; the CloudFormation provider schema retains that responsibility.
- Provider-schema findings for `DefinitionSubstitutions` and E3601 findings for
  `Definition` are accumulated independently. Neither owner's success, rejection,
  or deferral removes or reclassifies the other owner's result.
- E3601's keyword collection contains exactly the object-valued `Definition` path.
  `DefinitionString` remains intentionally disabled even though the provider schema
  exposes both interfaces.
- Declaration recognition is scoped to the concrete owning state machine obtained
  from `validator.context.path.path`. Keys from another resource never defer a
  placeholder in this definition.
- Every string leaf in the object-valued `Definition` is eligible, regardless of
  nesting depth. Recursive schema validation supplies the leaf and its ASL path.
- Ordinary ASL validation happens first. Deferred-error filtering happens second,
  followed by the existing message-path decoration, rule assignment, and cleaning.
- A declaration authorizes only a failing string that directly contains its
  supported placeholder. It does not authorize its containing state, sibling
  states, or the definition as a whole.
- Missing or malformed declarations grant no exemption. Unrelated ASL failures are
  emitted with their existing path, schema path, rule ownership, and ordering.
- A failing string is an indivisible concrete-constraint instance: all referenced
  keys across all supported tokens must be owned, or no part of that string's
  failure is filtered.
- With no supported placeholder in an object-valued definition, every filter
  decision retains the ordinary ASL result, so both acceptance and rejection are
  observationally unchanged.
- Validation is synchronous and read-only. There is no retry, persistence,
  compensation, rollback, queue, scheduled work, or asynchronous completion path.
