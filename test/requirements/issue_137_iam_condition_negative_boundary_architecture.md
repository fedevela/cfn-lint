# Issue 137 IAM Condition Negative-Boundary Architecture

This record gives every IAMCOND-009 and IAMCOND-010 logic obligation an
implementation-ready structural home. It extends the positive operator
architecture in `issue_136_iam_condition_operator_architecture.md`, records
placement and contracts only, and changes no production runtime behavior.

## Requirement and verification placement

| Requirement | Verification obligation | Procedures | Owning locus |
| --- | --- | --- | --- |
| IAMCOND-009 | `test_iamcond_009_given_unknown_unsupported_or_malformed_operator_when_e3510_validates_then_error_path_ends_at_that_operator`; `test_iamcond_009_given_malformed_operator_alongside_corrected_operator_when_e3510_validates_then_malformed_error_remains_and_corrected_operator_adds_no_error` | `reject_unrecognized_condition_operator`; `validate_e3510_condition_negative_boundary` | `policy.json#/definitions/Condition` owns the closed operator vocabulary through fully anchored `patternProperties`, explicit properties, and `additionalProperties: false`; E3510 transports the resulting operator-local error |
| IAMCOND-010 | `test_iamcond_010_given_set_qualified_condition_key_maps_to_non_array_when_e3510_validates_then_value_is_rejected_at_operator_and_key_path`; `test_iamcond_010_given_set_qualified_array_contains_non_string_compatible_elements_when_e3510_validates_then_each_is_rejected_at_policy_relative_array_path`; `test_iamcond_010_given_each_set_condition_key_has_literal_strings_and_supported_cfn_string_expressions_when_object_policy_with_functions_is_validated_then_no_type_or_operator_errors` | `validate_set_qualified_condition_values`; `validate_e3510_condition_negative_boundary` | set-qualified patterns delegate to `policy.json#/definitions/ConditionSetValue`; its object, array, and string-item contracts combine with the existing CloudFormation function filter and function validators |

The authoritative bidirectional requirement, verification, procedure, and
architecture links are maintained in
`test/requirements/issue_137_iam_condition_negative_boundary_verification.json`.

## Architectural loci

### A1. Closed condition-operator vocabulary

- **Requirements:** IAMCOND-009.
- **Verifications:** both IAMCOND-009 functions named in the table above.
- **Procedures:** `reject_unrecognized_condition_operator` and
  `validate_e3510_condition_negative_boundary`.
- **Owner:**
  `src/cfnlint/data/schemas/other/iam/policy.json#/definitions/Condition`.
- **Responsibility:** recognize only complete, case-sensitive canonical operator
  names. Anchored `patternProperties` own grouped comparison-family recognition;
  explicit `BinaryEquals`, `Bool`, and `Null` properties own those names; and
  `additionalProperties: false` owns rejection of every unmatched property.
- **Incoming dependencies:** `Condition` references in `policy_identity.json`,
  `policy_resource.json`, and `policy_resource_ecr.json` resolve this shared
  definition through the store built by `Policy.__init__`.
- **Outgoing dependencies:** recognized set-qualified names select
  `ConditionSetValue`; recognized ordinary and `IfExists` names select
  `ConditionValue`; explicit properties retain their declared contracts.
- **Data and errors crossing the seam:** one operator property and its
  condition-key map enter schema evaluation. An unmatched property produces the
  existing pattern-mismatch `ValidationError` at the operator property path.
  Sibling properties remain independent inputs to the same object traversal.
- **State, lifecycle, and events:** none. Recognition is synchronous,
  read-only, invocation-local schema evaluation with no persistence or event.
- **Validation seam:** the malformed-operator parameter matrix and the
  malformed/corrected sibling scenario in the issue-specific unit module.
- **Implementation sequence:** preserve the exact anchored patterns established
  by Issue 136 and keep `additionalProperties: false`. Do not add aliases,
  pre-normalization, trimming, Python-side operator tables, or fail-fast sibling
  handling.

The compatibility vocabulary includes exactly singular `ForAnyValue:` and
`ForAllValues:` qualifiers for set-qualified names. `ForAnyValues:`, misspelled
families, leading or trailing whitespace, punctuation inserted into a family,
and any other extraneous character remain outside the contract.

### A2. Set-qualified value and string-context contract

- **Requirements:** IAMCOND-010.
- **Verifications:** all three IAMCOND-010 functions named in the table above.
- **Procedures:** `validate_set_qualified_condition_values` and
  `validate_e3510_condition_negative_boundary`.
- **Owner:**
  `src/cfnlint/data/schemas/other/iam/policy.json#/definitions/ConditionSetValue`.
- **Responsibility:** own the complete nested shape: the operator value is an
  object; every condition-key value is an array; and every array item occupies
  a string context. Container and item failures remain distinct and retain the
  path introduced by JSON Schema descent.
- **Incoming dependency:** only a recognized set-qualified pattern in A1
  delegates its condition-key map to this definition.
- **Outgoing dependencies:** array items use the existing `type: "string"`
  contract. When functions are enabled, `FunctionFilter` in
  `src/cfnlint/jsonschema/_filter.py` detects a supported singleton function
  object and presents that same string schema to its established function
  validator; `Ref` and `Fn::Sub` remain owned by their existing function rules.
- **Data and errors crossing the seam:** condition-key values descend first
  through the array type boundary and then by array index through the string
  item boundary. Literal strings or supported string-compatible expressions
  leave no type error. Scalar containers and incompatible items leave their
  existing errors at key or item paths respectively.
- **Error ownership:** ordinary schema type failures reach A3 for E3510 rule
  attachment. Errors emitted by `fn_*` or `cfnLint` collaborators retain their
  collaborating rule; IAM schema code does not translate them.
- **State, lifecycle, and recovery:** none. Each key and element is validated
  synchronously from immutable inputs. No cache, transaction, retry,
  compensation, queue, or rollback applies.
- **Validation seam:** the non-array value matrix, invalid array-element
  scenario, and the function-enabled multi-key `Ref`/`Fn::Sub` scenario.
- **Implementation sequence:** retain `ConditionSetValue` without widening it
  to scalar or generic object values and without duplicating function semantics
  in the IAM schema. Enable the inert verification cases during Malkhut and use
  executable evidence to decide whether any production edit is necessary.

### A3. Resolver, rule identity, and shared consumers

- **Requirements:** IAMCOND-009 and IAMCOND-010 directly through E3510; the
  shared A1 and A2 contracts also form compatibility surfaces for E3512 and
  E3513.
- **Verifications:** all five Issue 137 verification functions exercise this
  boundary through `IdentityPolicy.validate`.
- **Procedure:** `validate_e3510_condition_negative_boundary`.
- **Owners:** `Policy.py` owns shared-schema loading, resolver construction,
  validator evolution, object/string input selection, and error transport.
  `IdentityPolicy.py` owns rule E3510 and identity-policy property selection.
  The three specialized policy schemas own statement shape. `ResourcePolicy.py`
  and `ResourceEcrPolicy.py` own E3512/E3513 selection, not condition semantics.
- **Dependency direction:** concrete policy rules depend on `Policy`; `Policy`
  depends on packaged schemas and validator infrastructure; specialized schemas
  depend by `$ref` on the shared `policy` schema. The shared schema has no
  dependency on a concrete rule, specialized statement schema, or test.
- **Data and error flow:** a policy object, or decoded JSON string, enters the
  specialized schema. Validation errors leave with their instance and schema
  paths intact. `Policy.validate` attaches the active concrete rule only to
  ordinary schema errors and preserves function-owned errors. Invalid JSON
  strings retain the existing early return.
- **Synchronous seam:** schema resolution and validation occur in process during
  one rule invocation. There is no asynchronous seam, persistence boundary,
  authorization boundary, deployment topology, migration, or emitted event.
- **Compatibility:** identity and resource policy statement differences remain
  in their specialized schemas. A1 and A2 apply uniformly because every
  specialized `Condition` property references the same shared definition.
- **Validation seam:** `_validate_identity_policy` and
  `_validate_identity_policy_with_functions` in the issue-specific unit module;
  established identity, resource, and ECR policy suites are consumer regression
  seams.
- **Implementation sequence:** no Python or specialized-schema change is
  planned. Change this locus only if later executable evidence isolates a
  resolver, function-context, or error-transport defect independent of A1/A2.

### A4. Verification seam

- **Requirements:** IAMCOND-009 and IAMCOND-010.
- **Verifications and procedures:** the five exact verification names and three
  procedures recorded above.
- **Owner:**
  `test/unit/rules/resources/iam/test_identity_policy_condition_operators.py`.
- **Responsibility:** preserve policy-relative path assertions, both set
  qualifiers, malformed/corrected sibling independence, strict non-array and
  per-item rejection, and function-enabled string-context acceptance.
- **Dependencies:** helpers construct object-form identity policies and invoke
  public `IdentityPolicy.validate` with `CfnTemplateValidator`; the
  function-aware helper supplies `Context(functions=FUNCTIONS)`.
- **Data crossing the seam:** policy dictionaries enter; materialized error
  lists or an empty list are asserted. Expected paths cross statement,
  condition, operator, condition key, and optional array-index boundaries.
- **Contract and sequence:** placeholders remain explicitly skipped in this
  phase. Malkhut owns removing only the Issue 137 skip markers, then executing
  direct negative cases, function-aware acceptance, and shared-consumer
  regressions. Tests must use public rule behavior rather than private schema
  calls so resolver and error ownership remain covered.

### A5. Traceability owner

- **Requirements:** IAMCOND-009 and IAMCOND-010.
- **Verifications and procedures:** all names in the placement table.
- **Owner:**
  `test/requirements/issue_137_iam_condition_negative_boundary_verification.json`.
- **Responsibility:** preserve reciprocal links among requirements, production
  schema loci, named tests, pseudocode procedures, and this architecture record.
- **Dependencies and data:** documentation-only symbol and path references; no
  runtime consumer, state, or event.
- **Validation seam:** static comparison of every architecture entry in
  `artifacts` with its reciprocal entry under `requirements`.
- **Implementation sequence:** update both sides whenever a requirement gains or
  loses an architectural locus.

## Explicit non-owners

`src/cfnlint/data/AdditionalSpecs/Policies.json` is not in the E3510 resolver
path and does not own operator rejection or set-value shape. The function filter
and `Ref`/`Fn::Sub` rules own general CloudFormation expression semantics, but
they do not own IAM operator vocabulary or widen `ConditionSetValue`. No new
public interface, adapter, generated schema, migration, persistence layer,
queue, workflow, deployment configuration, observability component, or package
dependency is implicated.

## Implementation-ready change boundary

The production architecture remains confined to the existing shared `Condition`
and `ConditionSetValue` definitions. The current declarations already express
the required closed vocabulary and strict nested value contract, so this phase
plans no production edit and preserves runtime behavior. Malkhut should first
enable the five Issue 137 verification scenarios. A production change is
justified only if that executable evidence identifies a discrepancy within A1
or A2; it must not move responsibility into a concrete IAM rule or duplicate
CloudFormation function handling.
