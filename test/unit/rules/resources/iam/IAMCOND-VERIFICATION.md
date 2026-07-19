# Shared IAM Condition requirement-to-verification map

All selectors below are active in `test_iam_condition_contract.py`. Their
parametrized node IDs preserve the rule family, operator or entry point, input
shape, and expected outcome for focused harness validation.

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

## Verification to architecture

The owning loci, contracts, dependency direction, and implementation order are
recorded in `IAMCOND-ARCHITECTURE.md`.

| Verification selector prefix | Architectural loci |
| --- | --- |
| `test_IAMCOND_002_` | Shared condition schema; CloudFormation-aware JSON Schema engine |
| `test_IAMCOND_006_` | Shared condition schema; CloudFormation-aware JSON Schema engine |
| `test_IAMCOND_007_` | Shared condition schema; CloudFormation-aware JSON Schema engine |
| `test_IAMCOND_008_` | Shared condition schema; family policy schemas and rule delegates; policy normalization and finding ownership |
| `test_IAMCOND_009_` | Shared condition schema; policy normalization and finding ownership; CloudFormation-aware JSON Schema engine |
| `test_IAMCOND_010_` | Family policy schemas and rule delegates; policy normalization and finding ownership; provider entry-point boundary |
| `test_IAMCOND_011_` | Shared condition schema; family policy schemas and rule delegates |
| `test_IAMCOND_012_` | Shared condition schema; CloudFormation-aware JSON Schema engine |
| `test_IAMCOND_013_` | Shared condition schema; family policy schemas and rule delegates; policy normalization and finding ownership; CloudFormation-aware JSON Schema engine |

## Implementation and evidence

| Requirement(s) | Implementation artifact | Manifested behavior and harness evidence |
| --- | --- | --- |
| IAMCOND-002 | `policy.json#/definitions/Condition/additionalProperties` | Closes the top-level condition member namespace; `test_IAMCOND_002_*` observes the member-level finding for scalar, list, and object values in all three rule families. |
| IAMCOND-006, IAMCOND-007 | Existing `ConditionValue`, `ConditionSetValue`, `Null`, and `Booleans` contracts reached through corrected operator patterns | `test_IAMCOND_006_*` observes object-body enforcement for every recognized operator; all three `test_IAMCOND_007_*` matrices observe the preserved value shapes, including item-index findings below a context key for invalid list members. |
| IAMCOND-008, IAMCOND-012 | Corrected, fully anchored set-qualified patterns plus the existing unqualified and explicit operator schemas | `test_IAMCOND_008_*` and `test_IAMCOND_012_*` observe valid single- and multi-operator conditions across E3510, E3512, and E3513. |
| IAMCOND-009 | Closed shared Condition schema interpreted by the existing `FunctionFilter` and intrinsic-aware `additionalProperties` implementation | Both `test_IAMCOND_009_*` selectors observe preserved intrinsic behavior without false unknown-operator findings. |
| IAMCOND-010 | Shared schema delta reached after existing `Policy.validate` object/JSON-string normalization | `test_IAMCOND_010_*` compares finding paths and valid outcomes across all ten eligible entry points. |
| IAMCOND-011 | Existing optional family-schema `Condition` properties | `test_IAMCOND_011_*` observes that omission does not create a condition finding. |
| IAMCOND-013 | Shared Condition finding emitted within the existing exhaustive family-schema error stream | Both `test_IAMCOND_013_*` matrices observe the condition finding together with independent policy and principal findings. |
