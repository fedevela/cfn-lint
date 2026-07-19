# Issue 144 Batch compute-environment Type outcome architecture

This record assigns consistent
`AWS::Batch::ComputeEnvironment.Properties.Type` outcomes to the repository's
existing schema, region-grouping, decode, runner, validation, and integration
boundaries. It is an implementation plan and does not change production
behavior.

## Architectural loci

### L1 — Batch schema data owns the accepted resource-level domain

- **Paths:**
  `src/cfnlint/data/schemas/patches/extensions/all/aws_batch_computeenvironment/boto.json`,
  `src/cfnlint/data/schemas/providers/us_east_1/aws-batch-computeenvironment.json`,
  and the regional provider package manifests under
  `src/cfnlint/data/schemas/providers/*/__init__.py`
- **Requirements:** `BATCHTYPE-004`, `BATCHTYPE-009`, `BATCHTYPE-011`
- **Verifications:** all five Issue 144 verification names recorded in L6
- **Procedures:** `GROUP_SUPPORTED_BATCH_SCHEMA_REGIONS`,
  `VALIDATE_RESOURCE_LEVEL_BATCH_TYPE`, `EXPOSE_BATCH_TYPE_OUTCOME`, and
  `VERIFY_BATCH_TYPE_OUTCOME_CONSISTENCY`
- **Responsibility:** preserve the exact resource-level enum `MANAGED`,
  `UNMANAGED`, `managed`, and `unmanaged` in the all-region Batch extension
  patch and its primary materialization. Preserve the independent nested
  `ComputeResources.Type` enum rather than using it as a fallback or alias.
- **Incoming dependency:** schema maintenance discovers the resource-scoped
  extension directory and applies its JSON Patch operations to downloaded
  provider schemas; regional manifests declare whether a provider schema is
  materialized locally or resolved from the primary region.
- **Outgoing dependency:** `ProviderSchemaManager.get_resource_schema` loads
  the materialized JSON into a `Schema`, or copies the primary `Schema` for a
  manifest-cached region and marks the copy `is_cached`.
- **Data contract:** `/properties/Type/enum` is the authoritative accepted
  domain for the resource-level value. The generated primary schema is the
  packaged runtime representation; the extension patch is the durable
  maintenance correction that must survive regeneration.
- **Mutation and failure ownership:** maintenance owns patch application and
  generated file writes. Runtime consumers read schema content without
  mutation; schema loading failures are translated by the manager to
  `ResourceNotFoundError`.
- **Validation seam:** every Issue 144 execution consumes this same schema node
  through L2 and L5. No CLI-, API-, format-, or region-specific accepted-value
  table is permitted.

L1 is one compatibility unit: an implementation that changes the patch without
its packaged primary materialization can leave current runtime data stale, while
changing only the materialization allows later maintenance to erase the
contract.

### L2 — ProviderSchemaManager owns supported-region lookup and grouping

- **Path:** `src/cfnlint/schema/manager.py`
- **Requirements:** `BATCHTYPE-004`
- **Verifications:**
  `test_batchtype_004_every_supported_region_including_cached_primary_accepts_all_four_resource_type_spellings`
  and
  `test_batchtype_004_every_supported_region_rejects_invalid_value_at_resource_type_path`
- **Procedures:** `GROUP_SUPPORTED_BATCH_SCHEMA_REGIONS`,
  `VALIDATE_RESOURCE_LEVEL_BATCH_TYPE`, and
  `VERIFY_BATCH_TYPE_OUTCOME_CONSISTENCY`
- **Responsibility:** `get_resource_types(region)` identifies regions whose
  provider package exposes the Batch resource; `get_resource_schema` owns
  direct-versus-primary-cached resolution; and
  `get_resource_schemas_by_regions` emits direct non-primary schemas as
  singleton groups before one primary/cached group.
- **Incoming dependency:** ordered configured regions, regional provider
  manifests, the L1 schema data, registry-schema overlays, and manager caches.
- **Outgoing dependency:** `Properties.validate` receives `(regions, Schema)`
  groups and builds a region-scoped validator for each group.
- **State and lifecycle:** the manager owns only in-process import and lookup
  caches. `reset()` clears schema and type caches; repeated lookups may reuse
  wrappers but do not rewrite schema content or change the accepted domain.
- **Error contract:** a missing resource schema becomes
  `ResourceNotFoundError` and that region is omitted from grouping. A region
  outside the global supported `REGIONS` set remains the responsibility of
  `TemplateRunner`, which raises `InvalidRegionException` before rule
  execution.
- **Validation seam:** L6 discovers supported Batch regions with
  `get_resource_types`, then verifies complete unique grouping, primary-region
  presence, cached-region presence, and cached membership in the primary
  group before observing E3030 outcomes.

The manager remains generic. It must not depend on Batch values, E3030, input
format, or public interface identity.

### L3 — Shared decoder dispatch owns JSON/YAML semantic convergence

- **Paths:** `src/cfnlint/decode/decode.py`,
  `src/cfnlint/decode/cfn_yaml.py`, and `src/cfnlint/decode/cfn_json.py`
- **Requirement:** `BATCHTYPE-011`
- **Verifications:**
  `test_batchtype_011_equivalent_json_and_yaml_have_identical_resource_type_rule_ids_and_outcomes`
  and
  `test_batchtype_009_011_invalid_cli_api_json_yaml_findings_identify_resource_type_not_nested_type`
- **Procedures:** `DECODE_EQUIVALENT_BATCH_TEMPLATE`,
  `EXPOSE_BATCH_TYPE_OUTCOME`, and `VERIFY_BATCH_TYPE_OUTCOME_CONSISTENCY`
- **Responsibility:** `decode_str` owns in-memory API payload dispatch and
  `decode` owns filename/stdin dispatch; both delegate to `_decode`, using the
  marked YAML decoder first and the JSON decoder only for the existing eligible
  scanner-error fallback.
- **Incoming contracts:** the Python API supplies template text; the CLI runner
  supplies a filename or stdin source. JSON is accepted by the YAML-first path
  because its semantic object is YAML-compatible, not because the filename
  extension selects a parser.
- **Outgoing contract:** a decoded mapping plus an empty parse-finding list, or
  no lintable template plus existing E0000 findings. Key names and scalar
  strings are preserved; source marks may differ without entering enum
  membership, rule identity, or logical `Match.path`.
- **Error ownership:** file access, Unicode, construction, parser, scanner, and
  JSON fallback failures remain decoder-owned. They terminate downstream Batch
  validation and are never translated into E3030.
- **Lifecycle:** decoding is synchronous and has no persistent state, retry,
  event, queue, or asynchronous seam.

No new JSON/YAML normalization layer belongs here. Equivalent representations
must converge by producing the same semantic template consumed by L4 and L5.

### L4 — Runner convergence owns interface-independent execution

- **Paths:** `src/cfnlint/api.py`, `src/cfnlint/config.py`,
  `src/cfnlint/runner.py`, and `src/cfnlint/formatters/json.py`
- **Requirements:** `BATCHTYPE-004`, `BATCHTYPE-009`, `BATCHTYPE-011`
- **Verifications:** all five Issue 144 verification names recorded in L6,
  including
  `test_batchtype_009_cli_and_python_api_agree_on_resource_type_acceptance_or_rejection`,
  `test_batchtype_011_equivalent_json_and_yaml_have_identical_resource_type_rule_ids_and_outcomes`,
  and
  `test_batchtype_009_011_invalid_cli_api_json_yaml_findings_identify_resource_type_not_nested_type`
- **Procedures:** `DECODE_EQUIVALENT_BATCH_TEMPLATE`,
  `EXPOSE_BATCH_TYPE_OUTCOME`, `VALIDATE_RESOURCE_LEVEL_BATCH_TYPE`, and
  `VERIFY_BATCH_TYPE_OUTCOME_CONSISTENCY`
- **Responsibility:** `cfnlint.api.lint` adapts an in-memory string and
  `ManualArgs` to `ConfigMixIn`; the `cfn-lint` entry point adapts CLI arguments
  and files to `Runner`. With the ordinary rule collection, both surfaces
  converge on `Runner.validate_template`, `TemplateRunner.run`, and the same
  configured regions.
- **Execution contract:** `TemplateRunner` owns region validity, transform
  termination, optional graph construction, rule execution, metadata
  directives, and finding deduplication. It returns ordinary `Match` objects;
  it does not know whether the caller is API or CLI.
- **Surface adaptation:** the API returns `list[Match]`. The CLI sorts matches,
  and `JsonFormatter` exposes `Match.rule.id` as `Rule.Id` and `Match.path` as
  `Location.Path`; `Runner._exit` independently derives the documented bitwise
  process status from finding severity.
- **Error and lifecycle ownership:** API decode findings return directly. CLI
  decode findings enter ordinary formatting. Transform findings short-circuit
  rule execution. A nonzero CLI exit after emitting E3030 is a valid rejection
  outcome, not a retry condition.
- **Synchronous seam:** the production paths are synchronous. The subprocess
  and temporary file used for CLI observation belong to L6, not to production
  orchestration.

L4 must remain Batch-agnostic. Interface parity follows from shared delegation,
not from comparing or translating Batch results between surfaces.

### L5 — Properties and E3030 own resource-level validation and path identity

- **Paths:** `src/cfnlint/rules/resources/properties/Properties.py`,
  `src/cfnlint/rules/resources/properties/Enum.py`,
  `src/cfnlint/jsonschema/_keywords.py`, and `src/cfnlint/match.py`
- **Requirements:** `BATCHTYPE-004`, `BATCHTYPE-009`, `BATCHTYPE-011`
- **Verifications:** all five Issue 144 verification names recorded in L6
- **Procedures:** `VALIDATE_RESOURCE_LEVEL_BATCH_TYPE`,
  `EXPOSE_BATCH_TYPE_OUTCOME`, and `VERIFY_BATCH_TYPE_OUTCOME_CONSISTENCY`
- **Responsibility:** `Properties.validate` selects the L2 schema groups,
  extends a validator with each L1 schema, maps the `enum` keyword to E3030,
  and prepends `Properties` to schema-relative errors. `Enum` delegates
  concrete resource values to the shared exact enum keyword.
- **Incoming data:** a decoded resource object, configured validation regions,
  enabled child rules, and the read-only schema node for that resource and
  region group.
- **Outgoing contract:** accepted members yield no E3030. An unrelated literal
  yields an E3030 `Match` whose logical path is
  `Resources.BatchEnvironment.Properties.Type`; `JsonFormatter` may serialize
  the same path but does not create it.
- **Path isolation:** resource-level `Properties.Type` is validated against
  `/properties/Type/enum`. Nested `Properties.ComputeResources.Type` is reached
  only when validation descends through that separate property and definition;
  neither domain can substitute for the other.
- **Failure ownership:** the enum keyword owns mismatch detection, E3030 owns
  rule classification, `Properties` owns the property-boundary prefix, and the
  ordinary rule framework owns conversion from validation errors to matches.
  Unexpected rule failures retain the existing rule-error behavior.
- **Mutation and consistency:** validation reads templates and schemas without
  mutation, persistence, compensation, publication, or asynchronous work.
  Deduplication remains above this boundary in L4.

No case-folding or Batch-specific branch belongs in L5. Exact equality against
the schema-owned four-member domain preserves rejection of `invalid` and the
separation from nested `ComputeResources.Type`.

### L6 — Integration verification owns cross-boundary outcome evidence

- **Path:** `test/integration/test_batch_type_outcomes.py`
- **Requirements:** `BATCHTYPE-004`, `BATCHTYPE-009`, `BATCHTYPE-011`
- **Verifications:**
  `test_batchtype_004_every_supported_region_including_cached_primary_accepts_all_four_resource_type_spellings`,
  `test_batchtype_004_every_supported_region_rejects_invalid_value_at_resource_type_path`,
  `test_batchtype_009_cli_and_python_api_agree_on_resource_type_acceptance_or_rejection`,
  `test_batchtype_011_equivalent_json_and_yaml_have_identical_resource_type_rule_ids_and_outcomes`,
  and
  `test_batchtype_009_011_invalid_cli_api_json_yaml_findings_identify_resource_type_not_nested_type`
- **Procedure:** `VERIFY_BATCH_TYPE_OUTCOME_CONSISTENCY`, consuming
  `GROUP_SUPPORTED_BATCH_SCHEMA_REGIONS`,
  `DECODE_EQUIVALENT_BATCH_TEMPLATE`, `EXPOSE_BATCH_TYPE_OUTCOME`, and
  `VALIDATE_RESOURCE_LEVEL_BATCH_TYPE`
- **Responsibility:** exercise the production seams end to end: discover and
  group every supported Batch region, observe all four accepted values and one
  invalid value, compare CLI with API, compare JSON with YAML, and assert the
  exact resource-level E3030 path.
- **Incoming dependency:** public API imports, the installed `cfn-lint` console
  entry point, provider-manager public methods, `REGIONS`, `REGION_PRIMARY`,
  PyYAML encoding, `tmp_path`, and synchronous subprocess completion.
- **Outgoing dependency:** ordinary pytest discovery through the repository's
  `testpaths`, tox invocation, and CI. No production component depends on this
  module.
- **Contract:** helpers reduce native CLI JSON and API `Match` objects to the
  same `(rule id, logical path)` observation without changing the underlying
  result. Temporary-file writes are test-owned and scoped to `tmp_path`.
- **Lifecycle:** Malkhut removes only the module-level `NETZACH` skip after L1
  through L5 are confirmed. Verification names, parameter sets, region
  grouping assertions, and path assertions remain stable traceability anchors.

## Dependency direction and integration topology

```text
Batch extension patch -> packaged primary Batch schema
                                  |
regional provider manifests ------+
                                  v
                    ProviderSchemaManager
                    (lookup + region groups)
                                  |
JSON/YAML text -> shared decoder -> Runner / TemplateRunner <- CLI or API config
                                  |
                                  v
                    Properties resource boundary
                                  |
                                  v
                 E3030 exact enum keyword -> Match.path
                                  |
                   +--------------+--------------+
                   |                             |
              API list[Match]          CLI JsonFormatter + exit status

integration verification -> observes every boundary through public seams
```

Dependencies point toward generic schema, decode, runner, and validation
abstractions. The schema owns Batch domain data; shared mechanisms never depend
on Batch. There is no database, transaction, authorization, event, queue,
deployment, migration, or production asynchronous boundary in this issue.

## Implementation sequence

1. Inspect L1 as a single maintenance/runtime unit. Preserve the existing
   four-value resource enum in both the extension patch and packaged primary
   schema, and preserve the independent nested enum operation.
2. Confirm every L2-supported Batch region resolves either its direct schema or
   a primary-cached copy carrying the same L1 resource enum. If a later schema
   refresh introduces a direct regional materialization, correct it through the
   existing all-region patch and regenerate it rather than adding runtime
   normalization.
3. Preserve the L3 YAML-first dispatch and semantic scalar preservation. No
   format-specific Batch adapter is required.
4. Preserve L4's CLI/API convergence on `Runner.validate_template` and
   `TemplateRunner`; do not duplicate validation or outcome translation in a
   public surface.
5. Preserve L5's exact E3030 comparison and resource-property path prefix. Do
   not alter shared enum behavior or inspect the nested enum for a resource-level
   value.
6. Remove only the L6 module-level skip in Malkhut, then use the five named
   obligations for focused executable validation.

The observed repository state already supplies L1 through L5. The expected
implementation delta for Issue 144 is therefore activation of L6 unless
executable validation reveals concrete regional schema drift. No feature flag,
new interface, migration, adapter, retry policy, or rollout mechanism is
required.

## Traceability summary

| Requirement | Verification obligations | Procedures | Architectural loci |
| --- | --- | --- | --- |
| `BATCHTYPE-004` | `test_batchtype_004_every_supported_region_including_cached_primary_accepts_all_four_resource_type_spellings`; `test_batchtype_004_every_supported_region_rejects_invalid_value_at_resource_type_path` | `GROUP_SUPPORTED_BATCH_SCHEMA_REGIONS`; `VALIDATE_RESOURCE_LEVEL_BATCH_TYPE`; `VERIFY_BATCH_TYPE_OUTCOME_CONSISTENCY` | L1, L2, L4, L5, L6 |
| `BATCHTYPE-009` | `test_batchtype_009_cli_and_python_api_agree_on_resource_type_acceptance_or_rejection`; `test_batchtype_009_011_invalid_cli_api_json_yaml_findings_identify_resource_type_not_nested_type` | `VALIDATE_RESOURCE_LEVEL_BATCH_TYPE`; `EXPOSE_BATCH_TYPE_OUTCOME`; `VERIFY_BATCH_TYPE_OUTCOME_CONSISTENCY` | L1, L4, L5, L6 |
| `BATCHTYPE-011` | `test_batchtype_011_equivalent_json_and_yaml_have_identical_resource_type_rule_ids_and_outcomes`; `test_batchtype_009_011_invalid_cli_api_json_yaml_findings_identify_resource_type_not_nested_type` | `VALIDATE_RESOURCE_LEVEL_BATCH_TYPE`; `DECODE_EQUIVALENT_BATCH_TEMPLATE`; `EXPOSE_BATCH_TYPE_OUTCOME`; `VERIFY_BATCH_TYPE_OUTCOME_CONSISTENCY` | L1, L3, L4, L5, L6 |
