# Issue 142 Batch compute-environment Type architecture

This record assigns the isolated
`AWS::Batch::ComputeEnvironment.Properties.Type` correction to the existing
provider-schema extension boundary. It is an implementation plan and does not
change production behavior.

## Architectural loci

### L1 — Batch extension patch owns the correction

- **Path:**
  `src/cfnlint/data/schemas/patches/extensions/all/aws_batch_computeenvironment/boto.json`
- **Requirements:** `BATCHTYPE-001`, `BATCHTYPE-002`, `BATCHTYPE-003`,
  `BATCHTYPE-005`, `BATCHTYPE-006`
- **Verifications:**
  `test_batchtype_001_lowercase_resource_type_is_accepted`,
  `test_batchtype_002_uppercase_resource_type_remains_accepted`,
  `test_batchtype_003_unrelated_resource_type_is_rejected`,
  `test_batchtype_005_lowercase_unrelated_enum_remains_rejected`,
  `test_batchtype_006_each_nested_compute_resources_type_is_accepted`, and
  `test_batchtype_006_nested_type_case_drift_and_unrelated_values_are_rejected`
- **Procedures:** `APPLY_BATCH_COMPUTE_ENVIRONMENT_TYPE_SCHEMA_PATCH`,
  `VALIDATE_RESOURCE_ENUM_DOMAINS`
- **Responsibility:** replace only `/properties/Type/enum` with the exact
  resource-level domain `MANAGED`, `UNMANAGED`, `managed`, and `unmanaged`.
  Retain the separate JSON Patch operation for
  `/definitions/ComputeResources/properties/Type/enum` with exactly `EC2`,
  `FARGATE`, `FARGATE_SPOT`, and `SPOT`.
- **Incoming dependency:** `ProviderSchemaManager._patch_provider_schema`
  discovers this resource-named, all-region extension directory and loads its
  sorted JSON patch files.
- **Outgoing dependency:** the patch depends only on the CloudFormation
  provider schema's JSON Pointer structure and the `jsonpatch` contract.
- **Contract:** a JSON Patch array scoped by directory identity to
  `aws-batch-computeenvironment.json`. No runtime Python interface is added.
- **Failure ownership:** `ProviderSchemaManager` owns patch exception logging
  and continuation. This locus introduces no retry, compensation, or fallback.
- **Validation seam:** the six ordinary E3030 regression tests observe the
  materialized domain through `Properties`; no patch-specific test double is
  needed.

This is the authoritative correction locus because the repository already uses
resource-specific extension patches to preserve provider-schema corrections
across schema maintenance. Putting case normalization in E3030 would transfer
domain ownership to a shared mechanism and violate `BATCHTYPE-005` and
`BATCHTYPE-006`.

### L2 — Regional provider schema owns the runtime materialization

- **Path:**
  `src/cfnlint/data/schemas/providers/us_east_1/aws-batch-computeenvironment.json`
- **Requirements:** `BATCHTYPE-001`, `BATCHTYPE-002`, `BATCHTYPE-003`,
  `BATCHTYPE-006`
- **Verifications:** all Batch-specific verification names listed under L1
  except the unrelated Lambda isolation verification.
- **Procedures:** `APPLY_BATCH_COMPUTE_ENVIRONMENT_TYPE_SCHEMA_PATCH`,
  `VALIDATE_RESOURCE_ENUM_DOMAINS`
- **Responsibility:** carry the generated enum domains consumed by ordinary
  validation. The resource-level and nested `Type` members remain separate
  schema nodes and therefore separate accepted-value contracts.
- **Incoming dependency:** maintenance invokes
  `ProviderSchemaManager.patch_schemas`, which applies provider patches and then
  extension patches, each in sorted filename order, before writing the schema.
- **Outgoing dependency:** `ProviderSchemaManager.get_resource_schema` loads
  this schema into `Schema`; `get_resource_schemas_by_regions` may use the
  primary schema as the cached schema for requested regions without an
  independent Batch schema.
- **Data crossing the seam:** immutable validation metadata in JSON form; no
  user resource is mutated and no persistent application state is owned here.
- **Contract:** `/properties/Type/enum` exposes the four resource-level values;
  `/definitions/ComputeResources/properties/Type/enum` exposes the four nested
  values.
- **Failure ownership:** schema maintenance writes the schema state remaining
  after logged patch failures. Runtime lookup continues to own unavailable
  resource/region handling.
- **Validation seam:** the regression module supplies literal resource values
  and observes E3030 findings and property paths.

The generated schema is a dependent runtime artifact, not a second source of
truth. Implementation must regenerate it from L1 so the packaged JSON used by
the linter and the durable maintenance patch cannot drift.

### L3 — Existing validation boundary consumes exact enum contracts

- **Paths:** `src/cfnlint/rules/resources/properties/Properties.py`,
  `src/cfnlint/rules/resources/properties/Enum.py`, and
  `src/cfnlint/jsonschema/_keywords.py`
- **Requirements:** `BATCHTYPE-001`, `BATCHTYPE-002`, `BATCHTYPE-003`,
  `BATCHTYPE-005`, `BATCHTYPE-006`
- **Verifications:** all six verification names under L1
- **Procedure:** `VALIDATE_RESOURCE_ENUM_DOMAINS`
- **Responsibility:** `Properties` selects schemas by resource type and region,
  maps the `enum` keyword to E3030, and prefixes error paths with `Properties`.
  `Enum` delegates non-parameter enum checks to the shared JSON Schema keyword.
  The keyword compares a concrete instance exactly against the enum belonging
  to its current schema node.
- **Incoming dependency:** resources, configured regions, enabled child rules,
  and schemas supplied by `ProviderSchemaManager`.
- **Outgoing dependency:** `ValidationError` becomes an E3030 `RuleMatch`
  through the existing JSON Schema rule machinery.
- **Data crossing the seam:** resolved literal property values and read-only
  schema nodes enter; zero or more validation findings leave.
- **Contract:** exact member equality, with no normalization, case folding,
  mutation, persistence, retry, or asynchronous branch.
- **Error ownership:** the enum keyword identifies the rejected value and
  accepted domain; the rule layer owns E3030 classification; `Properties` owns
  the resource-property path prefix.
- **Validation seam:** Batch resource-level, Batch nested, and Lambda
  `PackageType` cases pass through the same comparator while retaining domains
  owned by their respective schema nodes.

L3 requires no production change. Its unchanged exact-comparison behavior is
the isolation mechanism required by `BATCHTYPE-005`.

### L4 — Ordinary regression module owns executable boundary evidence

- **Path:**
  `test/unit/rules/resources/properties/test_enum_batch_type.py`
- **Requirements:** `BATCHTYPE-001`, `BATCHTYPE-002`, `BATCHTYPE-003`,
  `BATCHTYPE-005`, `BATCHTYPE-006`, `BATCHTYPE-013`
- **Verifications:** all six test functions recorded in
  `batchtype-issue-142.json`
- **Procedure:** `VERIFY_BATCH_TYPE_REGRESSION_CONTRACT`
- **Responsibility:** exercise the production `Properties`/E3030 seam with
  lowercase and uppercase resource-level values, an unrelated resource-level
  value, Lambda case drift, every accepted nested value, and nested case drift
  and unrelated values.
- **Incoming dependency:** the shared `validator` fixture, `Properties`, E3030
  `Enum`, and materialized provider schemas.
- **Outgoing dependency:** ordinary pytest discovery and CI; no bespoke runner
  or external service.
- **Contract:** accepted cases yield no E3030 findings; rejected cases yield one
  E3030 finding at the exact property path and identify the rejected value.
- **Lifecycle:** the existing module-level NETZACH skip is removed only after L1
  and L2 are implemented together.

## Dependency direction and integration topology

```text
Batch extension patch (authoritative correction)
    -> schema maintenance / ProviderSchemaManager patching
    -> materialized regional Batch provider schema
    -> ProviderSchemaManager runtime lookup and region grouping
    -> Properties resource boundary
    -> E3030 Enum delegate
    -> shared exact jsonschema enum keyword
    -> ValidationError / RuleMatch

ordinary regression module
    -> observes the same production validation path
```

The dependency direction stays data-driven: the shared validator depends on a
schema-provided enum contract and does not depend on Batch. The Batch extension
patch depends on the generic patch loader but not on validation rules. There is
no queue, event, database, transaction, authorization boundary, deployment
topology change, or runtime asynchronous seam in this issue. Multiprocessing is
confined to maintenance-time regional schema patching; each regional schema
file remains independently owned and written.

## Implementation sequence

1. Update only the resource-level enum value in L1 to the four explicit
   spellings. Do not alter the nested enum operation or shared Python code.
2. Regenerate/patch provider schemas through the existing maintenance path so
   L2 materializes the L1 contract. Review the generated delta and retain only
   the affected Batch schema data.
3. Remove the module-level skip at L4 without changing its verification names or
   assertions.
4. In the executable validation phase, run the focused ordinary regression
   module and the workspace-required broader checks.

L1 and L2 form one compatibility change: landing only L1 leaves current
packaged runtime data stale, while landing only L2 allows the next schema
maintenance cycle to erase the correction. L4 activation follows both. No
migration, feature flag, compatibility adapter, or rollout sequencing is
required because the accepted domain is widened without removing uppercase
members.

## Traceability summary

| Requirement | Verification obligation | Procedures | Architectural loci |
| --- | --- | --- | --- |
| `BATCHTYPE-001` | `test_batchtype_001_lowercase_resource_type_is_accepted` | `APPLY_BATCH_COMPUTE_ENVIRONMENT_TYPE_SCHEMA_PATCH`; `VALIDATE_RESOURCE_ENUM_DOMAINS`; `VERIFY_BATCH_TYPE_REGRESSION_CONTRACT` | L1, L2, L3, L4 |
| `BATCHTYPE-002` | `test_batchtype_002_uppercase_resource_type_remains_accepted` | `APPLY_BATCH_COMPUTE_ENVIRONMENT_TYPE_SCHEMA_PATCH`; `VALIDATE_RESOURCE_ENUM_DOMAINS`; `VERIFY_BATCH_TYPE_REGRESSION_CONTRACT` | L1, L2, L3, L4 |
| `BATCHTYPE-003` | `test_batchtype_003_unrelated_resource_type_is_rejected` | `APPLY_BATCH_COMPUTE_ENVIRONMENT_TYPE_SCHEMA_PATCH`; `VALIDATE_RESOURCE_ENUM_DOMAINS`; `VERIFY_BATCH_TYPE_REGRESSION_CONTRACT` | L1, L2, L3, L4 |
| `BATCHTYPE-005` | `test_batchtype_005_lowercase_unrelated_enum_remains_rejected` | `APPLY_BATCH_COMPUTE_ENVIRONMENT_TYPE_SCHEMA_PATCH`; `VALIDATE_RESOURCE_ENUM_DOMAINS`; `VERIFY_BATCH_TYPE_REGRESSION_CONTRACT` | L1, L3, L4 |
| `BATCHTYPE-006` | `test_batchtype_006_each_nested_compute_resources_type_is_accepted`; `test_batchtype_006_nested_type_case_drift_and_unrelated_values_are_rejected` | `APPLY_BATCH_COMPUTE_ENVIRONMENT_TYPE_SCHEMA_PATCH`; `VALIDATE_RESOURCE_ENUM_DOMAINS`; `VERIFY_BATCH_TYPE_REGRESSION_CONTRACT` | L1, L2, L3, L4 |
| `BATCHTYPE-013` | all six ordinary regression verifications | `VERIFY_BATCH_TYPE_REGRESSION_CONTRACT` | L4 |

