# Issue 138 IAM Condition Entry-Point Architecture

This record gives IAMCOND-006 and every traced entry-point procedure an
implementation-ready structural home. It composes with the shared positive and
negative IAM Condition architecture in the Issue 136 and Issue 137 records,
records placement and contracts only, and changes no production runtime
behavior.

## Requirement and verification placement

| Requirement | Verification obligation | Procedures | Architectural loci |
| --- | --- | --- | --- |
| IAMCOND-006 | `test_iamcond_006_given_equivalent_valid_corrected_condition_when_each_e3510_owned_resource_type_is_linted_then_no_unsupported_operator_error` | `register_e3510_identity_policy_entry_points`; `validate_e3510_owned_policy_document`; `validate_all_e3510_identity_policy_entry_points` | A1 owns the six selectors; A2 carries every selected document to E3510; A3 delegates all documents to the shared Condition contract |
| IAMCOND-006 | `test_iamcond_006_given_group_role_or_user_with_multiple_policy_entries_when_corrected_operator_occurs_at_any_wildcard_location_then_e3510_accepts_that_entry` | `register_e3510_identity_policy_entry_points`; `validate_all_e3510_identity_policy_entry_points` | A1 declares the three wildcard selectors; A2 expands every concrete `Policies` index without changing the selector contract |
| IAMCOND-006 | `test_iamcond_006_given_genuine_condition_violation_at_each_owned_entry_point_when_template_is_linted_then_match_remains_e3510_with_full_owning_policy_path` | `validate_e3510_owned_policy_document`; `validate_all_e3510_identity_policy_entry_points` | A3 owns ordinary-error attribution; A2 and A4 preserve the concrete resource, policy, statement, condition, and invalid-member path |
| IAMCOND-006 | `test_iamcond_006_given_one_valid_corrected_condition_per_owned_resource_type_when_all_are_linted_together_then_entry_point_validation_is_independent_and_unchanged` | `validate_all_e3510_identity_policy_entry_points` | A2 owns invocation-per-document traversal; A4 records invocation-local lifecycle and accumulation |

The authoritative reciprocal requirement, verification, procedure, production,
and architecture links are maintained in
`test/requirements/issue_138_iam_condition_entry_point_verification.json`.

## Owned entry-point contract

| Resource type | E3510 selector owned by `IdentityPolicy` | Concrete data delivered to E3510 |
| --- | --- | --- |
| `AWS::IAM::Group` | `Resources/AWS::IAM::Group/Properties/Policies/*/PolicyDocument` | `Resources.<logical-id>.Properties.Policies[index].PolicyDocument` for every index |
| `AWS::IAM::ManagedPolicy` | `Resources/AWS::IAM::ManagedPolicy/Properties/PolicyDocument` | `Resources.<logical-id>.Properties.PolicyDocument` |
| `AWS::IAM::Policy` | `Resources/AWS::IAM::Policy/Properties/PolicyDocument` | `Resources.<logical-id>.Properties.PolicyDocument` |
| `AWS::IAM::Role` | `Resources/AWS::IAM::Role/Properties/Policies/*/PolicyDocument` | `Resources.<logical-id>.Properties.Policies[index].PolicyDocument` for every index |
| `AWS::IAM::User` | `Resources/AWS::IAM::User/Properties/Policies/*/PolicyDocument` | `Resources.<logical-id>.Properties.Policies[index].PolicyDocument` for every index |
| `AWS::SSO::PermissionSet` | `Resources/AWS::SSO::PermissionSet/Properties/InlinePolicy` | `Resources.<logical-id>.Properties.InlinePolicy` |

These six selectors are a closed E3510 ownership set for IAMCOND-006. The
provider schemas make the corresponding object/string properties and array
items traversable, but they do not own identity-policy semantics.

## Architectural loci

### A1. E3510 entry-point registry

- **Requirement:** IAMCOND-006.
- **Verifications:** the equivalent-entry-point and wildcard-location
  obligations in the placement table.
- **Procedure:** `register_e3510_identity_policy_entry_points`.
- **Owner:**
  `src/cfnlint/rules/resources/iam/IdentityPolicy.py#IdentityPolicy.__init__.keywords`.
- **Responsibility:** declare exactly the six ordered selectors in the owned
  entry-point contract and configure the shared `Policy` base with resolver ID
  `identity` and `policy_identity.json`. Rule ID E3510 remains on this concrete
  rule.
- **Incoming dependencies:** rule discovery and the `cfnLint` supplemental
  keyword compare the current structural CloudFormation path with this selector
  collection. Provider resource schemas expose the selected properties and the
  `Policies` item shape.
- **Outgoing dependencies:** construction delegates schema loading and policy
  validation to `Policy`; it introduces no resource-specific validator.
- **Data crossing the seam:** selector strings and one selected policy document.
  `*` denotes every array item and is not a stored or chosen concrete index.
- **Contract:** all six selectors use one concrete rule, schema identity, and
  specialized identity schema. Adding a seventh selector or transferring one
  to E3512/E3513 is outside IAMCOND-006.
- **Validation seam:** the six-case entry-point matrix and the group/role/user
  two-index matrix in `test_identity_policy_entry_points.py`.
- **Implementation sequence:** preserve the current selector collection. Change
  this locus only if Malkhut evidence finds a missing, extra, or misspelled
  registration.

### A2. Provider-schema traversal and wildcard expansion

- **Requirement:** IAMCOND-006.
- **Verifications:** all four named obligations.
- **Procedures:** `register_e3510_identity_policy_entry_points` and
  `validate_all_e3510_identity_policy_entry_points`.
- **Owners:** provider schemas for IAM group, managed policy, standalone policy,
  role, user, and SSO permission set own their resource property shapes;
  `src/cfnlint/jsonschema/_keywords.py#properties` and `#items` own synchronous
  descent; `src/cfnlint/jsonschema/_filter.py#FunctionFilter._filter_schemas`
  exposes the structural path to the `cfnLint` keyword; and
  `src/cfnlint/rules/jsonschema/CfnLint.py#CfnLint.cfnLint` dispatches the rule
  whose selector equals that path.
- **Responsibility:** descend through every resource property and every array
  item, represent an item as `*` only in the structural selector path, and
  invoke E3510 once for each concrete policy document reached.
- **Incoming dependencies:** `Properties.validate` selects each resource schema
  by type and establishes the `Resources/<type>/Properties` structural context.
- **Outgoing dependencies:** each matched document is passed synchronously to
  `IdentityPolicy.validate`, inherited from `Policy`; traversal continues after
  accepted documents and emitted errors.
- **Data and path crossing the seam:** the policy value crosses as an object or
  string. The structural path carries resource type and wildcard matching; the
  instance path independently retains logical ID, property names, and concrete
  array index for diagnostics.
- **State and lifecycle:** descent is invocation-local and read-only. There is
  no shared cursor, selected-index state, short-circuit flag, persistence, or
  event publication.
- **Validation seam:** public `cfnlint.lint` calls in all four issue-specific
  verification functions cover registration, wildcard expansion, combined
  traversal, and resource-path composition.
- **Implementation sequence:** no traversal or provider-schema edit is planned.
  A production change here requires executable evidence of a generic traversal
  defect, not merely an IAM operator mismatch.

### A3. Identity-policy and shared Condition contract

- **Requirement:** IAMCOND-006.
- **Verifications:** the equivalent-entry-point and genuine-violation
  obligations.
- **Procedure:** `validate_e3510_owned_policy_document`.
- **Owners:** `src/cfnlint/rules/resources/iam/Policy.py` owns schema loading,
  resolver construction, object/string selection, validator evolution, and
  error classification. `policy_identity.json` owns identity statement shape
  and delegates `Statement.Condition` to
  `policy.json#/definitions/Condition`. That shared definition owns corrected
  operator recognition and value-contract selection under the Issue 136/137
  architecture.
- **Incoming dependency:** every A1 selector reaches the same `Policy.validate`
  method with the `identity` resolver store containing both specialized and
  shared schemas.
- **Outgoing dependencies:** recognized operators delegate to `ConditionValue`
  or `ConditionSetValue`; supported CloudFormation expressions retain their
  existing function-rule collaborators.
- **Data and errors crossing the seam:** an object policy is validated with the
  caller's CloudFormation context; a string policy is JSON-decoded and validated
  with functions disabled. Ordinary schema errors leave with E3510 attached.
  `fn_*` and `cfnLint` errors retain their collaborating owner. Undecodable JSON
  preserves the established early return.
- **Contract:** no entry point may copy, specialize, or override the corrected
  operator vocabulary. Uniformity follows from all six paths resolving the same
  shared `Condition` definition.
- **Validation seam:** successful corrected operators and an unsupported
  operator at each of the six resource paths.
- **Implementation sequence:** implement shared operator changes only at the
  Issue 136/137 schema loci. Modify this boundary only if later evidence
  isolates resolver, input-representation, or rule-classification behavior.

### A4. Diagnostic path and independent accumulation boundary

- **Requirement:** IAMCOND-006.
- **Verifications:** the genuine-violation and combined-template-independence
  obligations.
- **Procedures:** `validate_e3510_owned_policy_document` and
  `validate_all_e3510_identity_policy_entry_points`.
- **Owner:**
  `src/cfnlint/rules/jsonschema/Base.py#BaseJsonSchema._convert_validation_errors_to_matches`
  owns concatenation of the concrete outer path with the policy-relative error
  path. The enclosing validator traversal owns accumulation of every yielded
  match.
- **Incoming dependencies:** A2 supplies the concrete resource/document prefix;
  A3 supplies policy-relative paths and the classified rule.
- **Outgoing data:** `RuleMatch` carries E3510 plus the full logical resource,
  concrete policy index where applicable, `PolicyDocument` or `InlinePolicy`,
  statement, condition, and invalid-member path.
- **Lifecycle and failure handling:** every selected document gets a fresh
  validator evolution. An error is yielded and accumulated without preventing
  traversal of sibling entries or later resources. There is no transaction,
  retry, compensation, rollback, queue, asynchronous completion, or recovery
  workflow.
- **Contract:** combined and isolated validation are observationally equivalent
  for the same immutable document, schemas, context, and enabled rule set.
- **Validation seam:** compare the combined six-resource result with six
  isolated results; assert E3510 and exact full paths for invalid documents.
- **Implementation sequence:** retain established error transport and
  accumulation. Do not add fail-fast or cross-document mutable state.

### A5. Verification and activation seam

- **Requirement:** IAMCOND-006.
- **Verifications and procedures:** all four verification functions and all
  three procedures in the placement table.
- **Owner:**
  `test/unit/rules/resources/iam/test_identity_policy_entry_points.py`.
- **Responsibility:** preserve the six-entry-point matrix, both concrete
  wildcard indices for group/role/user, exact E3510 path attribution, and
  combined-versus-isolated independence through the public lint boundary.
- **Dependencies and data:** resource factories build valid provider-shaped
  templates; the helper invokes `cfnlint.lint` with only E3510 enabled; matches
  or empty lists are asserted without private-schema calls.
- **Contract and sequence:** placeholders remain skipped in Yesod. Malkhut owns
  removing these four skip markers, executing the entry-point suite, and then
  executing the established identity-policy and shared-condition regressions.

### A6. Traceability owner

- **Requirement:** IAMCOND-006.
- **Verifications and procedures:** all names in the placement table.
- **Owner:**
  `test/requirements/issue_138_iam_condition_entry_point_verification.json`.
- **Responsibility:** preserve reciprocal links among the requirement,
  production loci, named tests, pseudocode procedures, and A1 through A6.
- **Dependencies, data, and lifecycle:** documentation-only repository paths
  and stable symbol anchors; no runtime dependency, mutation, or event.
- **Validation seam:** statically compare every `artifacts` entry with its
  reciprocal `requirements` entry whenever a locus changes.
- **Implementation sequence:** update both directions atomically with every
  architecture change.

## Dependency direction and explicit non-owners

The dependency direction is provider schema traversal -> concrete E3510
selector -> shared `Policy` validation -> identity statement schema -> shared
Condition schema. Diagnostics return in the reverse direction while preserving
the concrete path and active rule owner. The shared Condition schema does not
depend on `IdentityPolicy`, any provider schema, or tests.

`ResourcePolicy` (E3512) and `ResourceEcrPolicy` (E3513) consume the shared
Condition contract but do not own any IAMCOND-006 entry point. Role
`AssumeRolePolicyDocument` is a trust-policy document and is deliberately not
in the E3510 selector set. `AdditionalSpecs/Policies.json`, generated provider
schema tooling, public API declarations, persistence, migrations, queues,
workflows, authorization, deployment configuration, and observability are not
owners of this entry-point continuity requirement.

## Implementation-ready change boundary

The current production structure already registers all six required paths and
routes them through one identity schema to the shared corrected Condition
contract. Therefore Yesod plans no production-source edit and preserves runtime
behavior. Malkhut should activate the four issue-specific verification
functions first. A production change is justified only by executable evidence
that isolates a discrepancy at A1 through A4; any such change must preserve the
ownership and dependency direction recorded here.
