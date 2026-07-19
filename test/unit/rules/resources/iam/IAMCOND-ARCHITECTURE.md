# Shared IAM Condition architecture

This record gives the procedures in `IAMCOND-PSEUDOCODE.md` concrete ownership,
boundaries, dependency direction, and implementation order. It describes the
smallest production change that can satisfy IAMCOND-002 and IAMCOND-006 through
IAMCOND-013 without changing runtime behavior during this architecture phase.

## Architectural decision

The shared IAM schema remains the ownership center for condition operator
recognition and operator-body value contracts. The implementation locus is
`src/cfnlint/data/schemas/other/iam/policy.json`, specifically
`definitions.Condition`, `definitions.ConditionValue`,
`definitions.ConditionSetValue`, and `definitions.Booleans`.

No Python condition validator, new rule, adapter, state store, event, or provider
schema is warranted. E3510, E3512, and E3513 already consume the shared contract
through family-schema `$ref` declarations, and the existing JSON Schema engine
already supplies the required additional-property paths, exhaustive keyword
iteration, intrinsic filtering, and value validation.

Implementation changes to `definitions.Condition` must be ordered as follows:

1. Correct every set-qualified `patternProperties` key so `^` precedes the full
   `ForAllValues:` or `ForAnyValues:` name and `$` follows the complete base
   operator. Correct the final `ForAnyValues:String(Not)?Like?` spelling to
   `ForAnyValues:String(Not)?Like`. This realizes
   `MATCH_RECOGNIZED_CONDITION_OPERATOR` before rejection is closed.
2. Add `additionalProperties: false` to `definitions.Condition`. This delegates
   unknown-member detection to the existing CloudFormation-aware
   `additionalProperties` validator after all intended operator variants are
   recognizable.
3. Remove the module-level skip from `test_iam_condition_contract.py` only in the
   implementation or validation phase, after the schema delta exists.

The three existing operator-body definitions remain unchanged. Their `type:
object` declarations already enforce IAMCOND-006, and their
`additionalProperties` schemas already own the three IAMCOND-007 value
contracts. The implementation must not consolidate these definitions or move
their behavior into a rule class.

## Requirement loci

| Requirement | Verification obligation(s) | Pseudocode procedure(s) | Owning architectural locus |
| --- | --- | --- | --- |
| IAMCOND-002 | `test_IAMCOND_002_unknown_top_level_member_is_rejected_beneath_condition` | `VALIDATE_SHARED_CONDITION`; `MATCH_RECOGNIZED_CONDITION_OPERATOR` | `policy.json#/definitions/Condition`: complete operator patterns plus `additionalProperties: false`; `_keywords_cfn.additionalProperties` preserves supported intrinsic names and `_keywords.additionalProperties` emits the member path. |
| IAMCOND-006 | `test_IAMCOND_006_each_recognized_operator_rejects_a_non_object_body` | `VALIDATE_SHARED_CONDITION`; `MATCH_RECOGNIZED_CONDITION_OPERATOR`; `VALIDATE_CONDITION_OPERATOR_BODY` | `policy.json#/definitions/Condition` routes explicit and patterned operators to `ConditionValue`, `ConditionSetValue`, or the `Null` object schema; each body contract owns `type: object`. |
| IAMCOND-007 | `test_IAMCOND_007_condition_value_operators_preserve_context_value_shapes`;<br>`test_IAMCOND_007_set_operators_preserve_array_only_context_value_shapes`;<br>`test_IAMCOND_007_null_operator_preserves_boolean_context_value_shapes` | `VALIDATE_SHARED_CONDITION`; `MATCH_RECOGNIZED_CONDITION_OPERATOR`; `VALIDATE_CONDITION_OPERATOR_BODY` | `policy.json#/definitions/ConditionValue`, `ConditionSetValue`, `Booleans`, and `Boolean` retain context-key value ownership. |
| IAMCOND-008 | `test_IAMCOND_008_recognized_well_structured_condition_remains_valid_per_family` | `CONFIGURE_IAM_POLICY_RULE_FAMILY`; `VALIDATE_IAM_POLICY_DOCUMENT`; `VALIDATE_SHARED_CONDITION`; `VALIDATE_CONDITION_OPERATOR_BODY` | `policy_identity.json`, `policy_resource.json`, and `policy_resource_ecr.json` retain family statement ownership and refer to `policy#/definitions/Condition`; the three rule classes retain family selection. |
| IAMCOND-009 | `test_IAMCOND_009_supported_intrinsic_in_place_of_condition_operator_is_not_unknown`;<br>`test_IAMCOND_009_supported_intrinsics_keep_existing_embedded_policy_outcomes` | `VALIDATE_IAM_POLICY_DOCUMENT`; `VALIDATE_SHARED_CONDITION`; `VALIDATE_CONDITION_OPERATOR_BODY` | `FunctionFilter` retains whole-value intrinsic delegation; `_keywords_cfn.additionalProperties` retains the top-level member exemption; `Policy.validate` retains object context and disables functions only after JSON-string parsing. |
| IAMCOND-010 | `test_IAMCOND_010_object_and_json_string_representations_have_equivalent_outcomes` | `CONFIGURE_IAM_POLICY_RULE_FAMILY`; `VALIDATE_IAM_POLICY_DOCUMENT` | `Policy.validate` owns object/string normalization once for all families; rule `keywords` and effective provider schemas own entry-point eligibility. |
| IAMCOND-011 | `test_IAMCOND_011_statement_without_optional_condition_has_no_condition_finding` | `VALIDATE_IAM_POLICY_DOCUMENT`; `VALIDATE_SHARED_CONDITION` | Each family statement schema exposes `Condition` in `properties` but omits it from `required`; no new default or invocation hook is introduced. |
| IAMCOND-012 | `test_IAMCOND_012_multiple_operators_and_context_keys_remain_accepted` | `VALIDATE_IAM_POLICY_DOCUMENT`; `VALIDATE_SHARED_CONDITION`; `MATCH_RECOGNIZED_CONDITION_OPERATOR`; `VALIDATE_CONDITION_OPERATOR_BODY` | `patternProperties`, `properties`, and nested `additionalProperties` retain exhaustive per-member descent; no `oneOf`, cardinality constraint, or short-circuiting layer is added. |
| IAMCOND-013 | `test_IAMCOND_013_condition_finding_does_not_suppress_independent_findings`;<br>`test_IAMCOND_013_condition_finding_does_not_suppress_invalid_principal` | `CONFIGURE_IAM_POLICY_RULE_FAMILY`; `VALIDATE_IAM_POLICY_DOCUMENT`; `VALIDATE_SHARED_CONDITION` | Family schemas retain Version, Statement, Effect, Action, Resource, Principal, and unsupported-property contracts; `Policy.validate` retains full `iter_errors` streaming and finding attribution. |

## Architectural loci

### Shared condition schema

- **Requirements:** IAMCOND-002, IAMCOND-006, IAMCOND-007, IAMCOND-008,
  IAMCOND-009, IAMCOND-011, IAMCOND-012, IAMCOND-013.
- **Verification:** every selector except the representation-entry-point matrix,
  which crosses this locus after normalization.
- **Procedures:** `VALIDATE_SHARED_CONDITION`,
  `MATCH_RECOGNIZED_CONDITION_OPERATOR`, and
  `VALIDATE_CONDITION_OPERATOR_BODY`.
- **Owner:** `src/cfnlint/data/schemas/other/iam/policy.json`.
- **Incoming dependency:** the three family schemas reference the shared
  `Condition` definition through the resolver store configured by `Policy`.
- **Outgoing dependency:** standard JSON Schema keywords descend into the three
  existing operator-body contracts; there is no application-layer callback.
- **Data crossing the seam:** the present `Statement.Condition` object and its
  document path. The schema and instance remain read-only.
- **Contract:** explicit `BinaryEquals`, `Bool`, and `Null` properties; fully
  anchored unqualified and set-qualified operator patterns; closed top-level
  membership; unchanged context-key value schemas.
- **Failure contract:** an unknown top-level name produces the owning rule's
  `additionalProperties` finding at
  `Statement/<index>/Condition/<member>` regardless of member value shape. A
  recognized operator with a scalar or list body produces a `type` finding at
  `Statement/<index>/Condition/<operator>`.
- **Test seam:** `test_iam_condition_contract.py` operator, body, value, intrinsic,
  multiplicity, omission, and independent-finding matrices.
- **Implementation order:** repair full-name patterns, close the Condition
  object, then activate the tests.

### Family policy schemas and rule delegates

- **Requirements:** IAMCOND-008, IAMCOND-010, IAMCOND-011, IAMCOND-013.
- **Verification:** `test_IAMCOND_008_*`, `test_IAMCOND_010_*`,
  `test_IAMCOND_011_*`, and both `test_IAMCOND_013_*` selectors.
- **Procedure:** `CONFIGURE_IAM_POLICY_RULE_FAMILY`.
- **Owners:** `policy_identity.json`, `policy_resource.json`, and
  `policy_resource_ecr.json`, selected by `IdentityPolicy`, `ResourcePolicy`, and
  `ResourceEcrPolicy` respectively.
- **Incoming dependency:** resource-property dispatch selects a registered
  keyword on E3510, E3512, or E3513.
- **Outgoing dependency:** each family schema depends on the shared schema's
  stable `$id` `policy` and `Condition` JSON Pointer. Family-specific statement
  requirements do not flow back into the shared schema.
- **Data crossing the seam:** a normalized IAM policy document; findings return
  synchronously under the owning family rule.
- **Contract:** identity policies exclude principals; resource policies require
  a principal and resource choice; ECR policies require a principal but keep
  resource optional. `Condition` stays optional in every family.
- **Test seam:** the common `RULE_CASES` matrix plus principal-only E3512/E3513
  coverage.
- **Implementation order:** no production edit; preserve these `$ref` and family
  contracts while changing their shared dependency.

### Policy normalization and finding ownership

- **Requirements:** IAMCOND-008, IAMCOND-009, IAMCOND-010, IAMCOND-013.
- **Verification:** `test_IAMCOND_008_*`, both `test_IAMCOND_009_*`,
  `test_IAMCOND_010_*`, and both `test_IAMCOND_013_*` selectors.
- **Procedure:** `VALIDATE_IAM_POLICY_DOCUMENT`.
- **Owner:** `src/cfnlint/rules/resources/iam/Policy.py`.
- **Incoming dependency:** each concrete family rule supplies keywords, schema
  name, and schema file to `Policy`.
- **Outgoing dependency:** `Policy` loads packaged schema resources, constructs
  the resolver store, evolves the incoming validator, and iterates the selected
  family schema.
- **Data crossing the seam:** object-form policies pass with incoming function
  context; valid JSON strings become parsed values with functions disabled;
  invalid JSON strings retain the established no-IAM-schema-finding outcome.
- **Contract:** stream all schema findings; assign the concrete family rule only
  when the finding is not owned by an `fn_*` or `cfnLint` validator.
- **Lifecycle and failure ownership:** validation is synchronous, stateless, and
  read-only. There is no persistence, transaction, queue, event publication,
  retry, compensation, recovery job, authorization boundary, or deployment
  topology change.
- **Test seam:** the ten-entry-point object/JSON-string matrix and independent
  finding matrices.
- **Implementation order:** no production edit; the schema delta enters through
  the existing resolver and iteration seam.

### CloudFormation-aware JSON Schema engine

- **Requirements:** IAMCOND-002, IAMCOND-006, IAMCOND-007, IAMCOND-009,
  IAMCOND-012, IAMCOND-013.
- **Verification:** unknown-member paths, all body/value matrices, intrinsic
  preservation, multiplicity, and independent findings.
- **Procedures:** `VALIDATE_SHARED_CONDITION` and
  `VALIDATE_CONDITION_OPERATOR_BODY`.
- **Owners:** `src/cfnlint/jsonschema/_filter.py`, `_keywords.py`,
  `_keywords_cfn.py`, `_utils.py`, and `validators.py`.
- **Incoming dependency:** `Policy` evolves the shared `CfnTemplateValidator`
  with the family schema and resolver.
- **Outgoing dependency:** schema keyword implementations consume declarative
  contracts; IAM schemas do not import validator internals.
- **Contract:** `FunctionFilter` delegates a single supported intrinsic used as
  a complete value; CloudFormation `additionalProperties` suppresses an extra
  whose name fully matches an enabled intrinsic; `find_additional_properties`
  excludes names matching `properties` or `patternProperties`; `properties` and
  `patternProperties` descend every applicable member; `iter_errors` yields all
  findings.
- **Test seam:** existing IAM tests establish intrinsic and multi-finding
  behavior, while `test_iam_condition_contract.py` pins the new contract.
- **Implementation order:** no engine edit. If schema-only implementation cannot
  satisfy these tests, stop and reassess this decision rather than broadening
  validator behavior implicitly.

### Provider entry-point boundary

- **Requirement:** IAMCOND-010.
- **Verification:**
  `test_IAMCOND_010_object_and_json_string_representations_have_equivalent_outcomes`.
- **Procedures:** `CONFIGURE_IAM_POLICY_RULE_FAMILY` and
  `VALIDATE_IAM_POLICY_DOCUMENT`.
- **Owners:** concrete rule `keywords` define rule reach; effective provider
  schemas define whether a selected property admits object, string, or both.
- **Incoming dependency:** CloudFormation resource-property validation identifies
  values at registered keyword paths.
- **Outgoing dependency:** eligible values are passed to the family rule and then
  `Policy.validate`; provider schemas do not depend on IAM condition internals.
- **Contract:** the object/string matrix contains four E3510 entry points, five
  E3512 entry points, and one E3513 entry point recorded in the pseudocode. IAM
  Role and User inline policy documents remain object-only and outside the
  IAMCOND-010 matrix; IAM Group inline policies remain object/string.
- **Test seam:** `OBJECT_OR_JSON_STRING_ENTRY_POINTS` asserts both keyword
  registration and equivalent policy outcomes.
- **Implementation order:** no provider schema or patch edit.

### Verification and traceability artifacts

- **Requirements:** IAMCOND-002, IAMCOND-006, IAMCOND-007, IAMCOND-008,
  IAMCOND-009, IAMCOND-010, IAMCOND-011, IAMCOND-012, IAMCOND-013.
- **Verification:** all named selectors in `IAMCOND-VERIFICATION.md`.
- **Procedures:** all five procedures in `IAMCOND-PSEUDOCODE.md`.
- **Owner:** `test/unit/rules/resources/iam/`.
- **Dependencies:** canonical requirement IDs map forward to verification,
  procedure, and production loci; the reverse map points each verification
  prefix back to its architectural seams.
- **Contract:** test placeholders remain inert in this phase and become the
  executable acceptance boundary only after implementation.
- **Implementation order:** schema implementation precedes skip removal and test
  execution.

## Dependency direction

```text
resource property selected by E3510 / E3512 / E3513 keyword
  -> concrete family rule
  -> Policy object/string normalization and resolver configuration
  -> identity / resource / ECR family schema
  -> policy#/definitions/Condition
  -> ConditionValue / ConditionSetValue / Booleans
  -> CloudFormation-aware JSON Schema keyword implementations
  -> ordered ValidationError stream attributed to the concrete family rule
```

The arrows describe runtime use, not source imports in both directions. Provider
schemas and concrete rules select the boundary; family schemas depend on the
shared `policy` schema; the schema engine interprets those contracts. Shared
condition behavior must not acquire dependencies on resource types, concrete
rule IDs, provider-schema patches, or tests.

## Compatibility and sequencing

- The `policy` schema `$id`, `definitions.Condition` pointer, family schema
  identifiers, rule IDs, keyword lists, and public rule classes remain stable.
- No schema migration or generated-provider update is required. `policy.json` is
  hand-maintained package data included by `pyproject.toml`'s `data/**/*.json`
  rule.
- Correcting recognized set-operator patterns before closing the object prevents
  intended IAM operators from becoming false unknown-member findings.
- Closing only `definitions.Condition` avoids affecting the open context-key
  namespaces intentionally modeled by `ConditionValue`, `ConditionSetValue`, and
  `Null`'s `additionalProperties` schemas.
- Existing family constraints and error accumulation remain independently
  evaluated, so the new condition finding cannot own or suppress unrelated
  policy defects.
- Documentation generation and deployment configuration are unaffected because
  no rule metadata, provider resource schema, public interface, or runtime
  topology changes.
