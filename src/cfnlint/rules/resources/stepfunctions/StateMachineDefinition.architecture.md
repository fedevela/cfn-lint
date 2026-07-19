# E3601 object-definition substitution architecture

Issue: `#126`

Runtime owner: `StateMachineDefinition.py`

Logic source: `StateMachineDefinition.pseudocode.md`

Verification source:
`test/unit/rules/resources/stepfunctions/test_state_machine_definition_substitutions.py`

## Decision

Substitution awareness is a private policy of E3601's object-valued `Definition`
validation path. It is implemented inside `StateMachineDefinition.py` as three
stateless collaborators around the existing `StateMachineDefinition.validate`
keyword hook. No public API, package boundary, ASL schema variant, provider-schema
change, persistence, or asynchronous integration is introduced.

Ordinary ASL validation remains authoritative. E3601 reads the owning state
machine's sibling `DefinitionSubstitutions`, validates the definition normally,
and filters only error-tree leaves whose failing string contains a placeholder
declared by key. Existing path decoration, rule assignment, and error cleaning run
after filtering.

## Architectural loci

### `E3601_VALIDATION_ORCHESTRATOR`

- Owner: `StateMachineDefinition.validate` in `StateMachineDefinition.py`.
- Requirements: `CFNSFN-001`, `CFNSFN-002`, `CFNSFN-003`, `CFNSFN-009`.
- Procedures: `validate_state_machine_definition`.
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

### `OWNING_SUBSTITUTION_KEY_READER`

- Owner: a private helper in `StateMachineDefinition.py` implementing
  `load_definition_substitution_keys`.
- Requirements: `CFNSFN-001`, `CFNSFN-003`, `CFNSFN-009`.
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
- Trust boundary: provider-schema validation, not E3601, owns whether every
  declaration value is CloudFormation-valid.

### `DECLARED_PLACEHOLDER_PREDICATE`

- Owner: a private pure helper in `StateMachineDefinition.py` implementing
  `string_contains_declared_substitution`.
- Requirements: `CFNSFN-001`, `CFNSFN-002`, `CFNSFN-003`, `CFNSFN-009`.
- Contract: receive an arbitrary ASL assertion instance and the immutable declared
  key set; return only a boolean deferral decision.
- Incoming dependency: `cfnlint.helpers.REGEX_SUB_PARAMETERS`, the workspace's
  existing complete `${...}` token grammar. Captured keys are normalized in the
  same manner as the pseudocode and compared by membership only.
- Boundary rule: non-strings, incomplete/literal tokens, and tokens without a
  declared key do not receive deferred treatment. The helper does not resolve or
  replace content and does not inspect the declaration value.

### `DEFERRED_ERROR_TREE_FILTER`

- Owner: a private pure recursive helper in `StateMachineDefinition.py`
  implementing `retain_non_deferred_failure`.
- Requirements: `CFNSFN-001`, `CFNSFN-002`, `CFNSFN-003`, `CFNSFN-009`.
- Contract: receive a fresh `ValidationError` tree and declared keys; return the
  unchanged error, a structurally equivalent error with filtered context, or
  `None` when every failing leaf is deferred.
- Incoming dependency: `DECLARED_PLACEHOLDER_PREDICATE` and the existing
  `ValidationError.instance/context` contract.
- Preservation rule: context order, validator, message, instance, path, schema
  path, rule metadata, and non-deferred child failures remain observable. If a
  partially retained node is copied, retained children are re-parented to that
  copy so absolute paths remain coherent.
- Failure boundary: required properties, additional properties, invalid
  containers, undeclared placeholders, and unrelated concrete-value failures are
  never suppressed merely because another error is deferred.

### `CLOUDFORMATION_DECLARATION_SCHEMA`

- Owner: the normal resource-properties/provider-schema validation path using the
  regional `src/cfnlint/data/schemas/providers/*/aws-stepfunctions-statemachine.json`
  artifacts.
- Requirements: `CFNSFN-003`, `CFNSFN-009`.
- Responsibility: continue validating the schema-permitted primitive declaration
  forms and CloudFormation intrinsic expressions. This locus is consumed as an
  independent validation boundary and is not changed by Issue #126.
- Dependency direction: E3601 may observe key presence but must not call into,
  duplicate, weaken, or replace this validation policy.

### `ASL_SCHEMA`

- Owner: `src/cfnlint/data/schemas/other/step_functions/statemachine.json` through
  the existing E3601 resolver.
- Requirements: `CFNSFN-001`, `CFNSFN-002`.
- Responsibility: remain the single source of concrete ASL structural, pattern,
  enum, format-equivalent, and discriminator constraints.
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
- Lifecycle: the module-level skip remains inert in this phase. Implementation
  validation removes that skip and runs these cases together with the existing
  `test_state_machine_definition.py` regression suite.

## Flow and dependency direction

```text
resource-property dispatcher
  -> StateMachineDefinition.validate
       -> Validator.context.path + Template.template (read sibling keys)
       -> ASL schema/resolver (ordinary synchronous validation)
       -> declared-placeholder predicate (pure membership decision)
       -> deferred error-tree filter (pure error selection)
       -> existing path decoration / rule ownership / error cleaning
  -> E3601 findings

provider-schema resource validation
  -> DefinitionSubstitutions value validity (independent findings)
```

The complete path is synchronous and invocation-local. It owns no durable state,
transaction, queue, event, retry, compensation, migration, configuration, or
deployment topology. Keys from one state machine cannot cross into another because
the concrete validator path determines the sibling lookup on every invocation.

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

## Implementation sequence

1. Add the three private collaborators to `StateMachineDefinition.py`, reusing
   `REGEX_SUB_PARAMETERS` and existing validator/template/error contracts.
2. Integrate them into `validate` after the current validator evolution and
   `iter_errors` call but before `_fix_message`, rule assignment, and `_clean_error`.
3. Remove only the Issue #126 module-level skip and execute its mapped verification
   obligations during the implementation-validation phase.
4. Execute the existing E3601 suite as the compatibility seam; no schema,
   provider-data, public-interface, packaging, or deployment change is sequenced.

This ordering keeps runtime behavior unchanged until implementation and makes the
smallest possible production delta independently reviewable.
