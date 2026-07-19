# E3601 object-definition substitution architecture

Issues: `#126`, `#127`, `#128`, `#129`

Runtime owner: `StateMachineDefinition.py`

Logic source: `StateMachineDefinition.pseudocode.md`

Verification sources:

- `test/unit/rules/resources/stepfunctions/test_state_machine_definition_substitutions.py`
- `test/unit/rules/resources/stepfunctions/test_state_machine_definition_substitution_ownership.py`
- `test/unit/rules/resources/stepfunctions/test_state_machine_definition_validation_continuity.py`
- `test/unit/rules/resources/stepfunctions/test_state_machine_validation_surface_boundaries.py`

## Decision

Substitution awareness is a private policy of E3601's object-valued `Definition`
validation path. It is implemented inside `StateMachineDefinition.py` as three
stateless collaborators around the existing `StateMachineDefinition.validate`
keyword hook. No public API, package boundary, ASL schema variant, provider-schema
change, persistence, or asynchronous integration is introduced.

Ordinary ASL validation remains authoritative. E3601 reads only the current owning
state machine's sibling `DefinitionSubstitutions`, validates the definition
normally, and filters only error-tree leaves whose complete failing string is
deferred. A failing string is deferred when it contains at least one supported
substitution token and every exact key referenced across all standalone, embedded,
and comma-delimited tokens is declared by that same resource. Existing path
decoration, rule assignment, and error cleaning run after filtering.

Issue #128 makes the preservation side of that boundary explicit. The complete
ASL schema remains the authority for concrete Task `Resource` values, required
and supported state fields, state-type discriminators, and `Next`/`End`
relationships. A declaration elsewhere in the definition cannot authorize the
suppression of those failures. When no failing string contains a declared
placeholder, the filter is observationally transparent: acceptance, validators,
paths, schema paths, rule ownership, context order, and emitted error order remain
those of the existing E3601 pipeline.

Issue #129 preserves the division between CloudFormation property validation and
E3601. The regional provider schema and the resource `Properties` rule continue
to own `DefinitionSubstitutions` container and value findings. E3601 receives
only the object-valued `Definition` instance selected by its registered keyword,
reads sibling declaration keys without validating their values, and filters only
its own ASL error trees. The provider schema's separate `DefinitionString`
property does not broaden E3601's intentionally object-only registration.

## Architectural loci

### `E3601_VALIDATION_ORCHESTRATOR`

- Owner: `StateMachineDefinition.validate` in `StateMachineDefinition.py`.
- Requirements: `CFNSFN-001`, `CFNSFN-002`, `CFNSFN-003`, `CFNSFN-004`,
  `CFNSFN-005`, `CFNSFN-006`, `CFNSFN-007`, `CFNSFN-008`, `CFNSFN-009`,
  `CFNSFN-010`, `CFNSFN-011`, `CFNSFN-012`.
- Procedures: `validate_state_machine_definition` and
  `preserve_state_machine_validation_surface_boundaries`.
- Responsibility: preserve the existing JSON-string/object split and ASL resolver,
  load declaration keys once per invocation, run ordinary ASL validation, pass each
  fresh error tree through the deferred-failure filter, and then retain the current
  `_fix_message`, rule-assignment, and `_clean_error` order.
- Incoming dependencies: the validator supplied by the resource-property keyword,
  `StateMachineDefinition.schema`, and `StateMachineDefinition.resolver`.
- Outgoing dependencies: the three private collaborators below and the existing
  E3601 error pipeline.
- Data crossing the seam: the current `Definition` instance, an immutable set of
  declaration keys, and `ValidationError` trees.
- Failure ownership: JSON parse failure and ASL validator behavior remain exactly
  as today; substitution lookup failure degrades to an empty key set rather than
  becoming acceptance or a new finding.
- Continuity contract: ASL validation always precedes filtering. The orchestrator
  never replaces deferred strings before schema evaluation and never short-circuits
  validation because a declaration exists elsewhere in the definition.
- Ownership contract: the orchestrator receives no provider-property
  `ValidationError` tree. Its deferred-error filter therefore has neither a
  dependency nor mutation authority over E3012/E3017 findings.

### `OWNING_SUBSTITUTION_KEY_READER`

- Owner: a private helper in `StateMachineDefinition.py` implementing
  `load_definition_substitution_keys`.
- Requirements: `CFNSFN-001`, `CFNSFN-003`, `CFNSFN-004`, `CFNSFN-005`,
  `CFNSFN-006`, `CFNSFN-007`, `CFNSFN-008`, `CFNSFN-009`, `CFNSFN-011`,
  `CFNSFN-012`.
- Contract: receive `Validator`; return `frozenset[str]` (or an equivalently
  immutable read-only set) containing sibling declaration keys.
- Incoming dependencies: `validator.context.path.path` for the concrete resource
  locus and `validator.cfn.template` for the transformed template tree.
- Boundary rule: only a path ending in `Properties/Definition` may be translated
  to `Properties/DefinitionSubstitutions`. Traversal must require mapping
  ancestors. A missing path or non-mapping sibling returns an empty set.
- Data ownership: the `Template` owns the declaration mapping. E3601 neither
  resolves nor copies declaration values; it snapshots keys only. Therefore a
  string, integer, boolean, zero, false, or intrinsic value has identical meaning
  to this reader.
- Lifecycle and isolation: the key set is recomputed from the concrete path on
  every E3601 invocation, never merged with another resource, cached on the rule,
  or reused after the invocation. The logical resource ID remains part of the
  traversal path, making the state-machine resource the authorization owner.
- Trust boundary: provider-schema validation, not E3601, owns whether every
  declaration value is CloudFormation-valid.

### `DECLARED_PLACEHOLDER_PREDICATE`

- Owner: a private pure helper in `StateMachineDefinition.py` implementing
  `string_contains_declared_substitution`.
- Requirements: `CFNSFN-001`, `CFNSFN-002`, `CFNSFN-003`, `CFNSFN-004`,
  `CFNSFN-005`, `CFNSFN-006`, `CFNSFN-007`, `CFNSFN-008`, `CFNSFN-009`,
  `CFNSFN-011`, `CFNSFN-012`.
- Contract: receive an arbitrary ASL assertion instance and the immutable declared
  key set; return only a boolean deferral decision.
- Incoming dependency: `cfnlint.helpers.REGEX_SUB_PARAMETERS`, the workspace's
  existing complete `${...}` outer-token grammar. The predicate owns the narrower
  Step Functions authorization policy layered on those captures: split every
  captured body on commas, preserve exact key text, reject empty components, and
  require every referenced key across every token to belong to the invocation's
  declared-key set.
- Boundary rule: non-strings, strings without a supported token,
  incomplete/literal tokens, partially declared embedded strings, and partially
  declared comma-delimited forms do not receive deferred treatment. One authorized
  key cannot authorize an otherwise unsupported string. The helper does not
  resolve or replace content and does not inspect declaration values.

### `DEFERRED_ERROR_TREE_FILTER`

- Owner: a private pure recursive helper in `StateMachineDefinition.py`
  implementing `retain_non_deferred_failure`.
- Requirements: `CFNSFN-001`, `CFNSFN-002`, `CFNSFN-003`, `CFNSFN-004`,
  `CFNSFN-005`, `CFNSFN-006`, `CFNSFN-007`, `CFNSFN-008`, `CFNSFN-009`,
  `CFNSFN-011`, `CFNSFN-012`.
- Contract: receive a fresh `ValidationError` tree and declared keys; return the
  unchanged error, a structurally equivalent error with filtered context, or
  `None` when every failing leaf is deferred.
- Incoming dependency: `DECLARED_PLACEHOLDER_PREDICATE` and the existing
  `ValidationError.instance/context` contract.
- Preservation rule: context order, validator, message, instance, path, schema
  path, rule metadata, and non-deferred child failures remain observable. If a
  partially retained node is copied, retained children are re-parented to that
  copy so absolute paths remain coherent.
- Failure boundary: concrete `Resource`, `Type`, and `Next` failures; required and
  additional properties; `requiredXor` transition/termination failures; invalid
  containers; undeclared placeholders; and unrelated concrete-value failures are
  never suppressed merely because another error is deferred.
- Error translation: an unauthorized or partially authorized string is not
  translated into a new error. Its original ASL failure remains in the tree and
  continues through E3601's established rule and path normalization pipeline.

### `CLOUDFORMATION_DECLARATION_SCHEMA`

- Owner: `Properties.validate` in
  `src/cfnlint/rules/resources/properties/Properties.py`, its E3012/E3017 child
  rules, and the regional
  `src/cfnlint/data/schemas/providers/*/aws-stepfunctions-statemachine.json`
  artifacts.
- Requirements: `CFNSFN-003`, `CFNSFN-009`, `CFNSFN-010`.
- Procedures: `preserve_state_machine_validation_surface_boundaries`.
- Responsibility: validate the `DefinitionSubstitutions` object shape and each
  value through the provider-schema branch. The schema permits strings, integers,
  booleans, and the validator's established CloudFormation intrinsic handling;
  zero and false remain type-valid rather than being interpreted by truthiness.
- Finding contract: container type failures remain E3012 findings and invalid
  value alternatives remain provider-owned E3012/E3017 findings at their original
  property paths. They enter the lint result independently of any E3601 finding
  retained or deferred for `Definition`.
- Dependency direction: E3601 may observe key presence but must not call into,
  duplicate, weaken, replace, or filter this validation policy. Provider
  validation does not depend on E3601 or its declared-placeholder predicate.

### `E3601_KEYWORD_REGISTRATION`

- Owner: `StateMachineDefinition.__init__` in `StateMachineDefinition.py`, with
  dispatch performed by the existing E1101 `cfnLint` keyword hook.
- Requirements: `CFNSFN-013`.
- Procedures: `register_e3601_definition_surface` and
  `preserve_state_machine_validation_surface_boundaries`.
- Contract: expose exactly
  `Resources/AWS::StepFunctions::StateMachine/Properties/Definition` in
  `StateMachineDefinition.keywords`. The commented `DefinitionString` keyword is
  an intentionally disabled compatibility boundary associated with issue #3518,
  not a second active interface.
- Incoming dependencies: provider-schema traversal supplies a matching property
  keyword and instance to E1101; E1101 compares that exact keyword with each child
  rule's registered keywords.
- Outgoing dependency: only a matching object-valued `Definition` dispatches to
  `E3601_VALIDATION_ORCHESTRATOR` and the ASL schema. `DefinitionString` retains
  its provider-schema contract but has no E3601/ASL-schema edge.
- Compatibility and lifecycle: provider schemas may continue exposing both
  definition interfaces without changing E3601's registration. Registration is
  initialized once per rule instance and owns no mutable per-template state.

### `ASL_SCHEMA`

- Owner: `src/cfnlint/data/schemas/other/step_functions/statemachine.json` through
  the existing E3601 resolver.
- Requirements: `CFNSFN-001`, `CFNSFN-002`, `CFNSFN-004`, `CFNSFN-005`,
  `CFNSFN-006`, `CFNSFN-007`, `CFNSFN-008`, `CFNSFN-011`, `CFNSFN-012`.
- Responsibility: remain the single source of concrete ASL structural, pattern,
  enum, format-equivalent, discriminator, required-property,
  additional-property, and `requiredXor` constraints. In particular, the Task
  schema owns `Resource`'s pattern and required status, `Type: Task`, `Next`'s
  non-empty pattern, and the exclusive `Next`/`End` relationship.
- Dependency direction: `E3601_VALIDATION_ORCHESTRATOR` validates against this
  schema first; `DEFERRED_ERROR_TREE_FILTER` interprets emitted errors afterward.
  The schema is not parameterized or cloned for CloudFormation substitutions.

### `ISSUE_126_VERIFICATION_SEAM`

- Owner:
  `test/unit/rules/resources/stepfunctions/test_state_machine_definition_substitutions.py`
  and `issue_126_traceability.json`.
- Requirements: `CFNSFN-001`, `CFNSFN-002`, `CFNSFN-003`, `CFNSFN-009`.
- Responsibility: construct a concrete `Path` and `Template`, invoke E3601 at its
  resource-property boundary, and verify Activity `Ref`, nested string constraints,
  declaration-value forms, falsy values, and complete-definition acceptance.
- Lifecycle: this seam is already executable after Issue #126 implementation and
  remains the compatibility boundary for the Issue #127 predicate change together
  with the existing `test_state_machine_definition.py` regression suite.

### `ISSUE_127_VERIFICATION_SEAM`

- Owner:
  `test/unit/rules/resources/stepfunctions/test_state_machine_definition_substitution_ownership.py`
  and `issue_127_traceability.json`.
- Requirements: `CFNSFN-004`, `CFNSFN-005`, `CFNSFN-011`.
- Procedures: `validate_state_machine_definition`,
  `load_definition_substitution_keys`, `string_contains_declared_substitution`,
  and `retain_non_deferred_failure`.
- Contract: construct one- and two-resource templates, preserve each concrete
  `Resources/<logical-id>/Properties/Definition` path, invoke E3601 through its
  resource-property boundary, and observe the Task `Resource` pattern finding.
- Coverage responsibility: verify undeclared standalone placeholders, declaration
  isolation between owners, fully declared embedded and comma-delimited forms, and
  the two partially declared negative forms.
- Lifecycle: the verification module is active. Harness validation covers this
  seam together with the Issue #126 and existing E3601 regression suites.

### `ISSUE_128_VERIFICATION_SEAM`

- Owner:
  `test/unit/rules/resources/stepfunctions/test_state_machine_definition_validation_continuity.py`
  and `issue_128_traceability.json`.
- Requirements: `CFNSFN-006`, `CFNSFN-007`, `CFNSFN-008`, `CFNSFN-012`.
- Procedures: `validate_state_machine_definition`,
  `load_definition_substitution_keys`, `string_contains_declared_substitution`,
  and `retain_non_deferred_failure`.
- Contract: construct an object-valued definition and its concrete resource
  `Path`, optionally add one independently valid declared substitution, invoke
  E3601 through `StateMachineDefinition.validate`, and observe validator names and
  ASL-relative paths on retained errors.
- Coverage responsibility: preserve concrete Task `Resource` pattern validation;
  `required`, `additionalProperties`, and state `Type` enum failures; missing,
  conflicting, and invalid transition/termination values; and ordinary valid and
  invalid object-definition behavior when no placeholders occur.
- Lifecycle: the seam is executable. Its helper boundary matches the active Issue
  #126/#127 suites and introduces no production dependency. Atlas owns execution
  through the focused Malkhut harness target.

### `ISSUE_129_VERIFICATION_SEAM`

- Owner:
  `test/unit/rules/resources/stepfunctions/test_state_machine_validation_surface_boundaries.py`
  and `issue_129_traceability.json`.
- Requirements: `CFNSFN-010`, `CFNSFN-013`.
- Procedures: `preserve_state_machine_validation_surface_boundaries` and
  `register_e3601_definition_surface`.
- Contract: use the public full-template `lint` seam to observe provider findings
  and the absence of cross-rule suppression, then inspect the provider properties
  and E3601 keyword registration directly to pin the object-only dispatch seam.
- Coverage responsibility: preserve E3012/E3017 findings for malformed
  `DefinitionSubstitutions`; preserve provider acceptance for string, integer,
  boolean, zero, false, and intrinsic values while E3601 defers the corresponding
  placeholder; and prove that `DefinitionString` introduces no E3601 finding or
  registration.
- Lifecycle: this seam is intentionally inert until Malkhut removes its module
  skip and performs executable validation. It introduces no production,
  provider-schema, or dispatch dependency.

## Flow and dependency direction

```text
provider-schema resource validation
  -> Properties.validate + regional provider schema
       -> DefinitionSubstitutions shape/value findings (E3012/E3017)
  -> E1101 exact-keyword dispatch
       -> Definition -> StateMachineDefinition.validate
            -> Validator.context.path + Template.template (read sibling keys)
            -> ASL schema/resolver (ordinary synchronous validation)
            -> all-referenced-keys predicate (pure authorization decision)
            -> deferred error-tree filter (pure error selection)
            -> existing path decoration / rule ownership / error cleaning
            -> E3601 findings
       -> DefinitionString -/-> E3601 (no registered edge)

lint result
  <- independent provider-property findings
  <- independently retained E3601 findings
```

The complete path is synchronous, read-only, and invocation-local. It owns no
durable state, transaction, queue, event, retry, compensation, migration,
configuration, or deployment topology. Keys from one state machine cannot cross
into another because the concrete validator path determines the sibling lookup on
every invocation. Missing declarations and malformed token components fail closed
to ordinary E3601 validation; they do not create a separate recovery path.

Error ownership crosses no asynchronous seam. The ASL schema creates each
`ValidationError`; the filter may remove only an authorized string failure or copy
a composite node to retain children; E3601 then preserves the existing path
decoration, rule assignment, and cleaning lifecycle. There is no retry,
compensation, or alternate error translator.

The provider schema owns the declaration mapping data and its validity; the
current state-machine resource owns the declaration keys E3601 may observe. No
transaction or consistency protocol joins the provider and E3601 branches: both
read the transformed template synchronously, emit rule-owned findings, and rely on
the existing lint runner for collection and deduplication. Neither branch can
delete or translate the other's findings.

## Verification-to-locus map

- Activity `Ref` and complete-definition obligations:
  `E3601_VALIDATION_ORCHESTRATOR`, `OWNING_SUBSTITUTION_KEY_READER`,
  `DECLARED_PLACEHOLDER_PREDICATE`, `DEFERRED_ERROR_TREE_FILTER`,
  `CLOUDFORMATION_DECLARATION_SCHEMA`, `ASL_SCHEMA`, and
  `ISSUE_126_VERIFICATION_SEAM`.
- Pattern, enum, and format-equivalent nested-string obligations:
  `E3601_VALIDATION_ORCHESTRATOR`, `DECLARED_PLACEHOLDER_PREDICATE`,
  `DEFERRED_ERROR_TREE_FILTER`, `ASL_SCHEMA`, and
  `ISSUE_126_VERIFICATION_SEAM`.
- String, integer, true, zero, false, intrinsic, and combined key-presence
  obligations: `E3601_VALIDATION_ORCHESTRATOR`,
  `OWNING_SUBSTITUTION_KEY_READER`, `DECLARED_PLACEHOLDER_PREDICATE`,
  `DEFERRED_ERROR_TREE_FILTER`, `CLOUDFORMATION_DECLARATION_SCHEMA`, and
  `ISSUE_126_VERIFICATION_SEAM`.
- Issue #127 undeclared standalone obligation:
  `E3601_VALIDATION_ORCHESTRATOR`, `OWNING_SUBSTITUTION_KEY_READER`,
  `DECLARED_PLACEHOLDER_PREDICATE`, `DEFERRED_ERROR_TREE_FILTER`, `ASL_SCHEMA`,
  and `ISSUE_127_VERIFICATION_SEAM`.
- Issue #127 two-owner isolation obligation:
  `E3601_VALIDATION_ORCHESTRATOR`, `OWNING_SUBSTITUTION_KEY_READER`,
  `DECLARED_PLACEHOLDER_PREDICATE`, `DEFERRED_ERROR_TREE_FILTER`, `ASL_SCHEMA`,
  and `ISSUE_127_VERIFICATION_SEAM`.
- Issue #127 fully declared embedded and comma-delimited obligations:
  `E3601_VALIDATION_ORCHESTRATOR`, `OWNING_SUBSTITUTION_KEY_READER`,
  `DECLARED_PLACEHOLDER_PREDICATE`, `DEFERRED_ERROR_TREE_FILTER`, `ASL_SCHEMA`,
  and `ISSUE_127_VERIFICATION_SEAM`.
- Issue #127 partially declared embedded and comma-delimited obligations:
  `E3601_VALIDATION_ORCHESTRATOR`, `OWNING_SUBSTITUTION_KEY_READER`,
  `DECLARED_PLACEHOLDER_PREDICATE`, `DEFERRED_ERROR_TREE_FILTER`, `ASL_SCHEMA`,
  and `ISSUE_127_VERIFICATION_SEAM`.
- `CFNSFN-006` concrete invalid Task `Resource` obligation:
  `E3601_VALIDATION_ORCHESTRATOR`, `OWNING_SUBSTITUTION_KEY_READER`,
  `DECLARED_PLACEHOLDER_PREDICATE`, `DEFERRED_ERROR_TREE_FILTER`, `ASL_SCHEMA`,
  and `ISSUE_128_VERIFICATION_SEAM`.
- `CFNSFN-007` missing `Resource`, unsupported field, and invalid `Type`
  obligations: `E3601_VALIDATION_ORCHESTRATOR`,
  `OWNING_SUBSTITUTION_KEY_READER`, `DECLARED_PLACEHOLDER_PREDICATE`,
  `DEFERRED_ERROR_TREE_FILTER`, `ASL_SCHEMA`, and
  `ISSUE_128_VERIFICATION_SEAM`.
- `CFNSFN-008` missing, conflicting, and invalid `Next`/`End` obligations:
  `E3601_VALIDATION_ORCHESTRATOR`, `OWNING_SUBSTITUTION_KEY_READER`,
  `DECLARED_PLACEHOLDER_PREDICATE`, `DEFERRED_ERROR_TREE_FILTER`, `ASL_SCHEMA`,
  and `ISSUE_128_VERIFICATION_SEAM`.
- `CFNSFN-012` valid and invalid object-definition continuity obligations:
  `E3601_VALIDATION_ORCHESTRATOR`, `OWNING_SUBSTITUTION_KEY_READER`,
  `DECLARED_PLACEHOLDER_PREDICATE`, `DEFERRED_ERROR_TREE_FILTER`, `ASL_SCHEMA`,
  `ISSUE_128_VERIFICATION_SEAM`, and the existing
  `test_state_machine_definition.py` regression seam.
- `CFNSFN-010` invalid `DefinitionSubstitutions` shape and value obligations:
  `CLOUDFORMATION_DECLARATION_SCHEMA`, `E3601_VALIDATION_ORCHESTRATOR`, and
  `ISSUE_129_VERIFICATION_SEAM`.
- `CFNSFN-010` schema-valid string, integer, boolean, zero, false, and intrinsic
  value obligation: `CLOUDFORMATION_DECLARATION_SCHEMA`,
  `E3601_VALIDATION_ORCHESTRATOR`, `OWNING_SUBSTITUTION_KEY_READER`,
  `DECLARED_PLACEHOLDER_PREDICATE`, `DEFERRED_ERROR_TREE_FILTER`, `ASL_SCHEMA`,
  and `ISSUE_129_VERIFICATION_SEAM`.
- `CFNSFN-013` `DefinitionString` full-lint and registration obligations:
  `E3601_KEYWORD_REGISTRATION`, `E3601_VALIDATION_ORCHESTRATOR`, `ASL_SCHEMA`,
  and `ISSUE_129_VERIFICATION_SEAM`. The latter two are deliberately absent from
  the `DefinitionString` dependency path; the verification seam observes that
  negative edge.

## Implementation status

1. `DECLARED_PLACEHOLDER_PREDICATE` parses every regex capture into
   comma-separated exact keys and requires a non-empty, universally declared
   referenced-key collection.
2. `OWNING_SUBSTITUTION_KEY_READER`, `DEFERRED_ERROR_TREE_FILTER`, and
   `E3601_VALIDATION_ORCHESTRATOR` retain their established contracts and ordering,
   providing the resource isolation and observable-failure boundaries required by
   Issue #127.
3. The Issue #127 verification seam is active for its six mapped obligations.
4. Issue #128 requires no new runtime locus: the ASL-first orchestration and
   exact-failing-string filter already place every continuity obligation at a
   cohesive owner. Its nine mapped verification cases are executable and
   nominated as the focused Malkhut harness surface.
5. Issue #129 requires no new runtime locus: provider-property validation,
   exact-keyword E1101 dispatch, and E3601's private error filter already establish
   the required ownership boundaries. Its five mapped verification obligations
   are inert until Malkhut.
6. The Issue #126 substitution suite and existing E3601 suite remain compatibility
   seams. No schema, provider-data, public-interface, packaging, or deployment
   change is required.

The architecture places Issue #129 entirely at existing synchronous validation
boundaries and leaves production runtime behavior, public interfaces, provider
data, packaging, and deployment topology unchanged.
