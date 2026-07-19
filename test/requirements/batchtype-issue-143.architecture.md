# Issue 143 Batch compute-environment Type structural architecture

This record assigns preservation of the
`AWS::Batch::ComputeEnvironment.Properties.Type` structural contract to the
existing provider-schema and resource-property validation boundaries. It is an
implementation plan and does not change production behavior.

## Architectural loci

### L1 — Provider schema owns the structural contract

- **Path:**
  `src/cfnlint/data/schemas/providers/us_east_1/aws-batch-computeenvironment.json`
- **Requirements:** `BATCHTYPE-007`, `BATCHTYPE-008`
- **Verifications:**
  `test_batchtype_007_omitted_resource_type_emits_e3003_at_properties_boundary`,
  `test_batchtype_008_null_resource_type_emits_e3012_string_contract_finding`,
  `test_batchtype_008_non_string_literal_emits_finding_and_is_not_accepted`, and
  `test_batchtype_007_008_accepted_string_passes_structure_and_preserves_domain`
- **Procedures:** `PRESERVE_BATCH_TYPE_STRUCTURAL_SCHEMA_CONTRACT`,
  `VALIDATE_BATCH_TYPE_STRUCTURAL_CONTRACT`
- **Responsibility:** retain `"Type"` in `/required`, retain `"string"` at
  `/properties/Type/type`, and carry the independently widened four-string
  domain at `/properties/Type/enum`.
- **Incoming dependency:** schema maintenance starts from the upstream provider
  schema and applies provider patches before extension patches. The Batch
  extension patch may replace the enum sibling but must not alter the required
  or type paths.
- **Outgoing dependency:** `ProviderSchemaManager.get_resource_schema` wraps the
  materialized JSON in `Schema`; `get_resource_schemas_by_regions` supplies it
  to `Properties`, including as the cached primary schema for regions without
  an independent file.
- **Data contract:** the three JSON Schema keywords are independent, read-only
  validation metadata. User resource values never enter schema ownership and
  are not normalized or persisted.
- **Failure ownership:** schema maintenance owns file writes after patching;
  runtime lookup owns unavailable resource/region handling by skipping the
  unavailable region and continuing with available schema groups.
- **Validation seam:** all four Issue 143 verifications consume these keyword
  declarations through the ordinary `Properties` boundary.

The materialized schema is the runtime authority for structure, but remains a
generated artifact. Its `/required` and `/properties/Type/type` members must
survive every regeneration while the extension patch preserves the accepted
domain correction.

### L2 — Batch extension patch owns only the enum delta

- **Path:**
  `src/cfnlint/data/schemas/patches/extensions/all/aws_batch_computeenvironment/boto.json`
- **Requirements:** `BATCHTYPE-007`, `BATCHTYPE-008`
- **Verifications:** all four verification names listed under L1
- **Procedure:** `PRESERVE_BATCH_TYPE_STRUCTURAL_SCHEMA_CONTRACT`
- **Responsibility:** add or replace only `/properties/Type/enum` with
  `MANAGED`, `UNMANAGED`, `managed`, and `unmanaged`. Preserve the separate
  nested `ComputeResources.Type` operation and every structural schema path.
- **Incoming dependency:** `ProviderSchemaManager._patch_provider_schema`
  discovers this all-region, resource-named extension directory and applies
  sorted JSON patch files after provider patches.
- **Outgoing dependency:** the patch depends only on the provider schema's JSON
  Pointer topology and the generic `jsonpatch` application contract.
- **Contract:** a resource-scoped JSON Patch array. It exposes no runtime Python
  interface and has no authority to change shared Required, Type, or Enum rule
  behavior.
- **Failure ownership:** `ProviderSchemaManager` classifies and logs patch
  conflicts, test failures, patch exceptions, pointer failures, and unknown
  exceptions, then continues without retry or compensation.
- **Lifecycle:** maintenance patches the primary region first and other regions
  through a process pool; each process mutates and writes only its regional
  schema file. Reapplying the same enum operation is deterministic with respect
  to the structural siblings.

This boundary prevents casing relaxation from becoming type relaxation. No
normalizer, coercion adapter, or Batch-aware branch belongs in E3012 or E3030.

### L3 — Existing Properties delegates keyword-specific validation

- **Paths:** `src/cfnlint/rules/resources/properties/Properties.py`,
  `src/cfnlint/rules/resources/properties/Required.py`,
  `src/cfnlint/rules/resources/properties/Type.py`,
  `src/cfnlint/rules/resources/properties/Enum.py`,
  `src/cfnlint/jsonschema/_keywords.py`, and
  `src/cfnlint/jsonschema/_keywords_cfn.py`
- **Requirements:** `BATCHTYPE-007`, `BATCHTYPE-008`
- **Verifications:** all four verification names listed under L1
- **Procedure:** `VALIDATE_BATCH_TYPE_STRUCTURAL_CONTRACT`
- **Responsibility:** `Properties` selects provider schemas by resource type and
  region, maps `required`, `type`, and `enum` to E3003, E3012, and E3030, and
  prefixes emitted paths with `Properties`. The three child rules retain their
  generic keyword ownership.
- **Incoming dependency:** a resolved resource object, configured regions,
  enabled child rules, and the schema groups supplied by
  `ProviderSchemaManager`.
- **Outgoing dependency:** keyword `ValidationError` instances are classified
  by the configured child rule and become ordinary lint findings.
- **Value and error contract:** missing `Type` yields E3003 at `Properties`;
  null, arrays, and objects fail the non-strict CloudFormation string check and
  yield E3012 at `Properties.Type`. The E3012 adapter classifies null as the
  existing JSON Schema `null` type so the keyword error is not discarded;
  booleans and numbers retain shared scalar compatibility but fail exact enum
  membership through E3030; accepted strings satisfy all three keywords and
  unrelated strings retain E3030.
- **Mutation and concurrency:** runtime validation reads resource values and
  schemas without mutation, persistence, retry, compensation, events, queues,
  or asynchronous work. Repeated calls with the same inputs follow the same
  provider-manager traversal order.
- **Compatibility boundary:** non-strict scalar behavior is repository-wide and
  remains unchanged. Exact enum comparison is the existing secondary rejection
  seam for boolean and numeric literals.

Harness evidence required a narrow production correction in L3: add `null` to
the E3012 adapter's exhaustive actual-type classification. This does not alter
shared type strictness or enum comparison; it exposes the error already emitted
by `cfn_type` and gives it the same `actual_type` metadata as every other JSON
type. The generic unit witness in
`test/unit/rules/resources/properties/test_value_primitive_type.py` protects this
adapter contract alongside the Batch boundary regression.

### L4 — Structural regression module owns executable evidence

- **Path:**
  `test/unit/rules/resources/properties/test_batch_type_structure.py`
- **Requirements:** `BATCHTYPE-007`, `BATCHTYPE-008`
- **Verifications:** all four verification names listed under L1
- **Procedure:** `VERIFY_BATCH_TYPE_STRUCTURAL_CONTRACT`
- **Responsibility:** exercise the production `Properties` seam with E3003,
  E3012, and E3030 attached; observe omission, null, boolean, number, array,
  object, accepted string, and unrelated string behavior at exact paths.
- **Incoming dependency:** the shared `validator` fixture, materialized provider
  schemas, and the unchanged Required, Type, and Enum implementations.
- **Outgoing dependency:** ordinary pytest discovery, tox, and CI; no custom
  runner, service, fixture schema, or test double.
- **Contract:** verification names and assertions remain stable as the durable
  acceptance interface recorded by `batchtype-issue-143.json`.
- **Lifecycle:** Malkhut removes the module-level `NETZACH` skip before focused
  executable validation. Activation follows confirmation that L1 and L2 remain
  structurally isolated.

## Dependency direction and integration topology

```text
upstream Batch provider schema
    -> ProviderSchemaManager maintenance patching
       -> Batch extension patch (enum path only)
    -> materialized regional Batch schema (required + type + enum)
    -> ProviderSchemaManager runtime lookup and region grouping
    -> Properties resource boundary
       -> E3003 Required keyword
       -> E3012 CloudFormation Type keyword
       -> E3030 exact Enum keyword
    -> ValidationError / RuleMatch

structural regression module
    -> observes the same production validation path
```

Dependencies remain data-driven and point toward generic schema and validation
abstractions. Shared validators do not depend on Batch, and the Batch patch does
not depend on rule implementations. There is no database, transaction,
authorization boundary, deployment change, event flow, queue, or runtime
asynchronous seam. Multiprocessing exists only in schema maintenance, with
regional files as independent write boundaries.

## Implementation sequence

1. Inspect L1 and L2 together and retain the existing isolated enum operation,
   top-level required member, and string declaration. Do not introduce a
   production delta when all three contracts already match.
2. If schema regeneration is required by another implementation delta, review
   every affected Batch regional materialization and reject any removal of
   `/required` or widening of `/properties/Type/type`.
3. Remove only the module-level skip at L4; preserve verification names,
   parameters, rule wiring, and assertions.
4. Ensure the E3012 adapter classifies `null` and yields the pre-existing
   `cfn_type` validation error with `actual_type := "null"`.
5. In Malkhut, nominate the focused structural regression module and the E3012
   adapter unit module for harness validation.

The patch and materialized schema are a single maintenance compatibility unit,
while the three schema keywords remain separate validation contracts. No
migration, feature flag, adapter, or rollout mechanism is required.

## Traceability summary

| Requirement | Verification obligation | Procedures | Architectural loci |
| --- | --- | --- | --- |
| `BATCHTYPE-007` | `test_batchtype_007_omitted_resource_type_emits_e3003_at_properties_boundary`; `test_batchtype_007_008_accepted_string_passes_structure_and_preserves_domain` | `PRESERVE_BATCH_TYPE_STRUCTURAL_SCHEMA_CONTRACT`; `VALIDATE_BATCH_TYPE_STRUCTURAL_CONTRACT`; `VERIFY_BATCH_TYPE_STRUCTURAL_CONTRACT` | L1, L2, L3, L4 |
| `BATCHTYPE-008` | `test_batchtype_008_null_resource_type_emits_e3012_string_contract_finding`; `test_batchtype_008_non_string_literal_emits_finding_and_is_not_accepted`; `test_batchtype_007_008_accepted_string_passes_structure_and_preserves_domain` | `PRESERVE_BATCH_TYPE_STRUCTURAL_SCHEMA_CONTRACT`; `VALIDATE_BATCH_TYPE_STRUCTURAL_CONTRACT`; `VERIFY_BATCH_TYPE_STRUCTURAL_CONTRACT` | L1, L2, L3, L4 |
