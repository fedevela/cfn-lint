# Issue 136 IAM Condition Operator Architecture

This record gives every IAMCOND-001 through IAMCOND-005 logic obligation an
implementation-ready structural home. It records placement and contracts only;
it does not change production runtime behavior.

## Requirement and verification placement

| Requirement | Verification obligation | Procedures | Owning locus |
| --- | --- | --- | --- |
| IAMCOND-001 | `test_iamcond_001_given_string_or_string_array_when_string_equals_if_exists_then_e3510_accepts`; `test_iamcond_001_002_003_given_parallelcluster_reproduction_when_e3510_validates_both_if_exists_and_set_qualified_occurrences_then_no_condition_operator_errors` | `define_shared_condition_operator_patterns`; `validate_shared_iam_condition`; `validate_e3510_identity_policy_condition_operators` | `policy.json#/definitions/Condition/patternProperties` recognizes `StringEqualsIfExists` and delegates to `ConditionValue`; E3510 remains the identity-policy entry point |
| IAMCOND-002 | `test_iamcond_002_given_string_array_when_for_any_value_string_equals_then_e3510_accepts`; ParallelCluster reproduction above | same three procedures | `policy.json#/definitions/Condition/patternProperties` recognizes `ForAnyValue:StringEquals` and delegates to `ConditionSetValue`; E3510 remains the identity-policy entry point |
| IAMCOND-003 | `test_iamcond_003_given_string_array_when_for_all_values_string_equals_then_e3510_accepts`; ParallelCluster reproduction above | same three procedures | `policy.json#/definitions/Condition/patternProperties` recognizes `ForAllValues:StringEquals` and delegates to `ConditionSetValue`; E3510 remains the identity-policy entry point |
| IAMCOND-004 | `test_iamcond_004_given_supported_comparison_family_when_correct_set_qualifier_and_array_values_then_shared_condition_accepts` (40 cases) | same three procedures | the set-qualified pattern family in `policy.json#/definitions/Condition/patternProperties`, with `ConditionSetValue` as its value contract |
| IAMCOND-005 | `test_iamcond_005_given_non_set_comparison_family_when_if_exists_with_established_values_then_shared_condition_accepts` (20 cases, each carrying scalar and array keys) | same three procedures | the ordinary/`IfExists` pattern family in `policy.json#/definitions/Condition/patternProperties`, with `ConditionValue` as its value contract |

The authoritative bidirectional requirement, verification, procedure, and
architecture links are maintained in
`test/requirements/issue_136_iam_condition_operator_verification.json`.

## Architectural loci

### A1. Shared condition contract owner

- **Requirements:** IAMCOND-001, IAMCOND-002, IAMCOND-003, IAMCOND-004,
  IAMCOND-005.
- **Verifications:** all six named functions in
  `test_identity_policy_condition_operators.py`.
- **Procedures:** `define_shared_condition_operator_patterns` and
  `validate_shared_iam_condition`.
- **Owner:**
  `src/cfnlint/data/schemas/other/iam/policy.json#/definitions/Condition`.
- **Responsibility:** recognize the exact, case-sensitive IAM operator property
  name and select its existing value schema. `additionalProperties: false`
  continues to own rejection of unsupported spellings.
- **Incoming dependencies:** the `Condition` properties in
  `policy_identity.json`, `policy_resource.json`, and
  `policy_resource_ecr.json` resolve `policy#/definitions/Condition` through
  the resolver store built by `Policy.__init__`.
- **Outgoing dependencies:** set-qualified patterns reference
  `#/definitions/ConditionSetValue`; ordinary and `IfExists` patterns reference
  `#/definitions/ConditionValue`; explicit `BinaryEquals`, `Bool`, and `Null`
  properties retain their current contracts.
- **Data crossing the seam:** a `Statement.Condition` object enters; each
  operator property carries a condition-key object. Set-qualified values remain
  arrays of strings. Ordinary and `IfExists` values remain boolean, number,
  string, or arrays of strings.
- **State and events:** none. JSON Schema evaluation is synchronous, read-only,
  invocation-local, and produces validation errors rather than events.
- **Validation seam:** the three named direct E3510 cases, the 40-case
  set-qualified matrix, the 20-case `IfExists` matrix, and the ParallelCluster
  fixture.
- **Implementation sequence:** first change only the affected
  `patternProperties` keys. Keep the `$ref` targets, value definitions,
  explicit properties, and `additionalProperties` unchanged.

The implementation patterns must place anchors around the entire property name.
The two accepted prefixes are exactly `ForAnyValue:` and `ForAllValues:`. The
20 family names are the matrix in
`issue_136_iam_condition_operator_logic.md`, including `Numeric`, not `Number`.
The non-set suffix is exactly optional `IfExists`, not `Exists`. Existing grouped
regular expressions may remain grouped when each expression denotes only matrix
members and selects one unambiguous contract. The malformed aliases currently
implied by misplaced anchors, `ForAnyValues:`, `Exists`, `Number`, or the
optional final character in the set-qualified `StringLike` pattern are not
compatibility contracts and must not be retained.

### A2. Shared schema resolver and error boundary

- **Requirements:** IAMCOND-001 through IAMCOND-005.
- **Verifications:** all six named verification functions exercise this boundary
  through `IdentityPolicy.validate`.
- **Procedure:** `validate_e3510_identity_policy_condition_operators`.
- **Owner:** `src/cfnlint/rules/resources/iam/Policy.py`.
- **Responsibility:** load `policy.json` together with a specialized policy
  schema, evolve the caller's validator, validate object or decoded string
  policy input, preserve CloudFormation-function errors, and attach the concrete
  policy rule to ordinary JSON Schema errors.
- **Incoming dependency:** `IdentityPolicy`, `ResourcePolicy`, and
  `ResourceEcrPolicy` configure the shared base with a schema identifier and
  specialized schema file.
- **Outgoing dependencies:** `load_resource`, `RefResolver`, and the evolved IAM
  validator consume the packaged JSON schemas.
- **Data and errors crossing the seam:** a policy object or JSON string enters;
  `ValidationError` instances with their original paths leave. Invalid JSON
  strings retain the existing early-return behavior.
- **Contract:** no new Python interface, adapter, cache, exception translation,
  or lifecycle hook is required. A condition-operator fix belongs below this
  boundary in A1.
- **Validation seam:** `_validate_identity_policy` in the issue-specific unit
  module and existing object/string tests in `test_identity_policy.py`.
- **Implementation sequence:** do not modify this locus unless later executable
  evidence proves the existing schema-resolution path is broken independently
  of operator recognition.

### A3. E3510 entry point and shared consumers

- **Requirements:** IAMCOND-001 through IAMCOND-005 directly through E3510; the
  same A1 contract is a compatibility surface for E3512 and E3513.
- **Verification:** the six issue-specific functions target E3510; existing
  resource-policy suites remain the regression seam for shared consumers.
- **Procedure:** `validate_e3510_identity_policy_condition_operators`.
- **Owners:** `IdentityPolicy.py` owns rule ID E3510 and its CloudFormation
  property selectors. `policy_identity.json` owns identity-statement shape.
  `ResourcePolicy.py`, `ResourceEcrPolicy.py`, `policy_resource.json`, and
  `policy_resource_ecr.json` are downstream consumers, not operator owners.
- **Dependency direction:** concrete rules depend on `Policy`; specialized
  schemas depend by `$ref` on the shared `policy` schema. The shared schema must
  not depend on a concrete rule or specialized schema.
- **Data ownership:** each concrete rule owns policy selection and diagnostic
  rule identity; A1 owns condition operator recognition and value shape.
- **Integration seam:** synchronous in-process JSON Schema references only.
  There is no persistence, transaction, queue, job, authorization boundary,
  retry, compensation, migration, deployment, or asynchronous topology change.
- **Compatibility:** correcting A1 intentionally makes the operator vocabulary
  available to all shared consumers while preserving each specialized
  statement contract, including identity/resource principal differences.
- **Implementation sequence:** no changes are planned in these files. Validate
  consumer compatibility after the A1 schema edit during the executable phase.

### A4. Verification and reproduction seam

- **Requirements:** IAMCOND-001 through IAMCOND-005.
- **Verifications:** the six exact names in
  `test/unit/rules/resources/iam/test_identity_policy_condition_operators.py`.
- **Procedures:** all three issue logic procedures.
- **Owners:** the issue-specific unit module owns the acceptance matrix;
  `issue_3777_parallelcluster_condition_operators.yaml` owns the reported
  end-to-end reproduction.
- **Incoming dependencies:** tests construct or decode policies and invoke the
  public `IdentityPolicy.validate` boundary with `CfnTemplateValidator`.
- **Outgoing data:** validation errors are materialized as a list; successful
  cases require an empty list.
- **Contract:** placeholders remain skipped in this architecture phase. Malkhut
  owns removal of skips and executable validation. Production implementation
  must not duplicate the 20-family matrix in Python.
- **Sequence:** implement A1, enable the issue tests, execute direct/matrix/
  reproduction coverage, then execute established IAM consumer regressions.

### A5. Traceability owner

- **Requirements, verifications, and procedures:** all listed above.
- **Owner:** `test/requirements/issue_136_iam_condition_operator_verification.json`.
- **Responsibility:** preserve bidirectional links among requirements, named
  tests, fixture, procedures, and this architecture record.
- **Dependencies:** documentation-only references to stable repository paths and
  symbols; no runtime consumer.
- **Validation seam:** static comparison of the `requirements` and `artifacts`
  sides of the mapping.
- **Sequence:** update this map whenever a requirement gains or loses an
  architectural locus.

## Explicit non-owners

`src/cfnlint/data/AdditionalSpecs/Policies.json` catalogs condition operators for
legacy/specification uses but is not in the E3510 resolver path. Its existing
`IfExists` spellings corroborate terminology; it does not own this correction
and requires no change. There are no generated schemas, migrations, persistence
adapters, deployment files, public APIs, or observability components implicated
by these requirements.

## Implementation-ready change boundary

The planned production delta is confined to the pattern keys under
`policy.json#/definitions/Condition/patternProperties`. No value contract,
Python class, specialized schema, package manifest, or runtime topology changes.
This placement satisfies all five requirements while keeping policy selection,
schema loading, error ownership, and shared-consumer behavior in their existing
cohesive loci.
