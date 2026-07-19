# Shared IAM Condition requirement-to-verification map

All selectors below are in `test_iam_condition_contract.py`. The module-level
skip keeps these placeholders inert while preserving pytest discovery and
parametrized node IDs for later executable validation.

The deterministic procedures that fulfill these obligations are recorded in
`IAMCOND-PSEUDOCODE.md`. Each procedure repeats its canonical requirement IDs
and complete verification selector names at the owning logic locus.

## Requirement to verification

| Requirement | Durable verification selector(s) |
| --- | --- |
| IAMCOND-002 | `test_IAMCOND_002_unknown_top_level_member_is_rejected_beneath_condition[shape-rule]` |
| IAMCOND-006 | `test_IAMCOND_006_each_recognized_operator_rejects_a_non_object_body[body-operator-rule]` |
| IAMCOND-007 | `test_IAMCOND_007_condition_value_operators_preserve_context_value_shapes[value-operator-rule]`; `test_IAMCOND_007_set_operators_preserve_array_only_context_value_shapes[value-operator-rule]`; `test_IAMCOND_007_null_operator_preserves_boolean_context_value_shapes[value-rule]` |
| IAMCOND-008 | `test_IAMCOND_008_recognized_well_structured_condition_remains_valid_per_family[rule]` |
| IAMCOND-009 | `test_IAMCOND_009_supported_intrinsic_in_place_of_condition_operator_is_not_unknown[rule]`; `test_IAMCOND_009_supported_intrinsics_keep_existing_embedded_policy_outcomes[rule]` |
| IAMCOND-010 | `test_IAMCOND_010_object_and_json_string_representations_have_equivalent_outcomes[scenario-entry-point]` |
| IAMCOND-011 | `test_IAMCOND_011_statement_without_optional_condition_has_no_condition_finding[rule]` |
| IAMCOND-012 | `test_IAMCOND_012_multiple_operators_and_context_keys_remain_accepted[rule]` |
| IAMCOND-013 | `test_IAMCOND_013_condition_finding_does_not_suppress_independent_findings[defect-rule]`; `test_IAMCOND_013_condition_finding_does_not_suppress_invalid_principal[rule]` |

## Verification to requirement

| Verification selector prefix | Requirement coverage |
| --- | --- |
| `test_IAMCOND_002_` | IAMCOND-002 |
| `test_IAMCOND_006_` | IAMCOND-006 |
| `test_IAMCOND_007_` | IAMCOND-007 |
| `test_IAMCOND_008_` | IAMCOND-008 |
| `test_IAMCOND_009_` | IAMCOND-009 |
| `test_IAMCOND_010_` | IAMCOND-010 |
| `test_IAMCOND_011_` | IAMCOND-011 |
| `test_IAMCOND_012_` | IAMCOND-012 |
| `test_IAMCOND_013_` | IAMCOND-013 |

## Shared and split coverage

- The rule matrix explicitly shares IAMCOND-002, IAMCOND-006, IAMCOND-007,
  IAMCOND-008, IAMCOND-009, IAMCOND-011, and IAMCOND-012 across E3510, E3512,
  and E3513.
- IAMCOND-007 is split by the shared schema's three established value contracts:
  `ConditionValue`, `ConditionSetValue`, and `Null`/`Booleans`.
- IAMCOND-009 is split between an intrinsic replacing a top-level condition
  operator and intrinsics at already-supported policy/condition value locations.
- IAMCOND-010 covers every registered rule keyword whose reviewed provider
  schema permits both object and JSON-string documents: four E3510 entry points,
  five E3512 entry points, and the E3513 entry point.
- IAMCOND-013 is split between common independent policy defects and the
  principal defect applicable only to resource and ECR policy families.

## Verification to logic

| Verification selector prefix | Procedure(s) in `IAMCOND-PSEUDOCODE.md` |
| --- | --- |
| `test_IAMCOND_002_` | `VALIDATE_SHARED_CONDITION`; `MATCH_RECOGNIZED_CONDITION_OPERATOR` |
| `test_IAMCOND_006_` | `VALIDATE_SHARED_CONDITION`; `MATCH_RECOGNIZED_CONDITION_OPERATOR`; `VALIDATE_CONDITION_OPERATOR_BODY` |
| `test_IAMCOND_007_` | `VALIDATE_SHARED_CONDITION`; `MATCH_RECOGNIZED_CONDITION_OPERATOR`; `VALIDATE_CONDITION_OPERATOR_BODY` |
| `test_IAMCOND_008_` | `CONFIGURE_IAM_POLICY_RULE_FAMILY`; `VALIDATE_IAM_POLICY_DOCUMENT`; `VALIDATE_SHARED_CONDITION`; `VALIDATE_CONDITION_OPERATOR_BODY` |
| `test_IAMCOND_009_` | `VALIDATE_IAM_POLICY_DOCUMENT`; `VALIDATE_SHARED_CONDITION`; `VALIDATE_CONDITION_OPERATOR_BODY` |
| `test_IAMCOND_010_` | `CONFIGURE_IAM_POLICY_RULE_FAMILY`; `VALIDATE_IAM_POLICY_DOCUMENT` |
| `test_IAMCOND_011_` | `VALIDATE_IAM_POLICY_DOCUMENT`; `VALIDATE_SHARED_CONDITION` |
| `test_IAMCOND_012_` | `VALIDATE_IAM_POLICY_DOCUMENT`; `VALIDATE_SHARED_CONDITION`; `MATCH_RECOGNIZED_CONDITION_OPERATOR`; `VALIDATE_CONDITION_OPERATOR_BODY` |
| `test_IAMCOND_013_` | `CONFIGURE_IAM_POLICY_RULE_FAMILY`; `VALIDATE_IAM_POLICY_DOCUMENT`; `VALIDATE_SHARED_CONDITION` |
