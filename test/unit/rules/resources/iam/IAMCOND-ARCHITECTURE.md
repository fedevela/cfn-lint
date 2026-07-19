# Shared IAM Condition architecture

This record gives the procedures in `IAMCOND-PSEUDOCODE.md` concrete ownership,
boundaries, dependency direction, and implementation order. It describes the
smallest production change satisfying IAMCOND-001 through IAMCOND-013.

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

Implementation changes to `definitions.Condition` were applied in this order:

1. Correct every set-qualified `patternProperties` key so `^` precedes the full
   `ForAllValues:` or `ForAnyValues:` name and `$` follows the complete base
   operator. Correct the final `ForAnyValues:String(Not)?Like?` spelling to
   `ForAnyValues:String(Not)?Like`. This realizes
   `MATCH_RECOGNIZED_CONDITION_OPERATOR` before rejection is closed.
2. Add `additionalProperties: false` to `definitions.Condition`. This delegates
   unknown-member detection to the existing CloudFormation-aware
   `additionalProperties` validator after all intended operator variants are
   recognizable.
3. Remove the module-level skip from `test_iam_condition_contract.py` after the
   schema delta exists.

The three existing operator-body definitions remain unchanged. Their `type:
object` declarations already enforce IAMCOND-006, and their
`additionalProperties` schemas already own the three IAMCOND-007 value
contracts. The implementation must not consolidate these definitions or move
their behavior into a rule class.

## Requirement loci

| Requirement | Verification obligation(s) | Pseudocode procedure(s) | Owning architectural locus |
| --- | --- | --- | --- |
| IAMCOND-001 | `test_IAMCOND_001_managed_policy_missing_operator_reports_error_E3510_at_condition_with_normal_and_information_selection[selection-mode]` | `RESOLVE_ISSUE_122_RULE_SELECTION`; `VALIDATE_ISSUE_122_IDENTITY_POLICY_ENTRY_POINTS`; `VALIDATE_IAM_POLICY_DOCUMENT`; `VALIDATE_SHARED_CONDITION`; `MATCH_RECOGNIZED_CONDITION_OPERATOR` | `ConfigMixIn.include_checks` preserves W/E defaults; Runner and E1101 dispatch the ManagedPolicy keyword to E3510; the closed shared Condition schema emits the missing-operator member path. |
| IAMCOND-002 | `test_IAMCOND_002_unknown_top_level_member_is_rejected_beneath_condition` | `VALIDATE_SHARED_CONDITION`; `MATCH_RECOGNIZED_CONDITION_OPERATOR` | `policy.json#/definitions/Condition`: complete operator patterns plus `additionalProperties: false`; `_keywords_cfn.additionalProperties` preserves supported intrinsic names and `_keywords.additionalProperties` emits the member path. |
| IAMCOND-003 | `test_IAMCOND_003_missing_operator_is_rejected_beneath_statement_condition_for_each_identity_policy_entry_point[entry-point]`;<br>`test_IAMCOND_003_include_checks_I_preserves_default_error_warning_selection_and_E3510_result` | `RESOLVE_ISSUE_122_RULE_SELECTION`; `VALIDATE_ISSUE_122_IDENTITY_POLICY_ENTRY_POINTS`; `VALIDATE_IAM_POLICY_DOCUMENT`; `VALIDATE_SHARED_CONDITION`; `MATCH_RECOGNIZED_CONDITION_OPERATOR` | `IdentityPolicy.keywords` owns all six resource-property paths; provider-schema E1101 dispatch and `Policy.validate` converge them on `policy_identity.json` and the shared closed Condition schema without changing E3510 selection or severity. |
| IAMCOND-004 | `test_IAMCOND_004_missing_operator_is_rejected_by_E3512_at_the_offending_condition_member_for_each_resource_policy_entry_point[entry-point]`;<br>`test_IAMCOND_004_recognized_nested_condition_has_no_missing_operator_E3512_finding_for_each_resource_policy_entry_point[entry-point]` | `VALIDATE_ISSUE_123_RESOURCE_POLICY_ENTRY_POINTS`; `CONFIGURE_IAM_POLICY_RULE_FAMILY`; `VALIDATE_IAM_POLICY_DOCUMENT`; `VALIDATE_SHARED_CONDITION`; `MATCH_RECOGNIZED_CONDITION_OPERATOR`; `VALIDATE_CONDITION_OPERATOR_BODY` | `ResourcePolicy.keywords` owns the five resource-property paths; provider-schema E1101 dispatch and `Policy.validate` converge them on `policy_resource.json` and the shared closed Condition schema while preserving E3512 attribution and concrete resource-relative prefixes. |
| IAMCOND-005 | `test_IAMCOND_005_missing_operator_is_rejected_by_E3513_at_the_offending_ECR_repository_policy_condition_member`;<br>`test_IAMCOND_005_recognized_nested_condition_has_no_missing_operator_E3513_finding_and_preserves_ECR_statement_acceptance` | `VALIDATE_ISSUE_124_ECR_REPOSITORY_POLICY`; `CONFIGURE_IAM_POLICY_RULE_FAMILY`; `VALIDATE_IAM_POLICY_DOCUMENT`; `VALIDATE_SHARED_CONDITION`; `MATCH_RECOGNIZED_CONDITION_OPERATOR`; `VALIDATE_CONDITION_OPERATOR_BODY` | `ResourceEcrPolicy.keywords` owns the ECR repository-policy path; provider-schema E1101 dispatch and `Policy.validate` converge it on `policy_resource_ecr.json` and the shared closed Condition schema while preserving E3513 attribution, the concrete repository-policy prefix, and ECR's optional Resource semantics. |
| IAMCOND-006 | `test_IAMCOND_006_each_recognized_operator_rejects_a_non_object_body` | `VALIDATE_SHARED_CONDITION`; `MATCH_RECOGNIZED_CONDITION_OPERATOR`; `VALIDATE_CONDITION_OPERATOR_BODY` | `policy.json#/definitions/Condition` routes explicit and patterned operators to `ConditionValue`, `ConditionSetValue`, or the `Null` object schema; each body contract owns `type: object`. |
| IAMCOND-007 | `test_IAMCOND_007_condition_value_operators_preserve_context_value_shapes`;<br>`test_IAMCOND_007_set_operators_preserve_array_only_context_value_shapes`;<br>`test_IAMCOND_007_null_operator_preserves_boolean_context_value_shapes` | `VALIDATE_SHARED_CONDITION`; `MATCH_RECOGNIZED_CONDITION_OPERATOR`; `VALIDATE_CONDITION_OPERATOR_BODY` | `policy.json#/definitions/ConditionValue`, `ConditionSetValue`, `Booleans`, and `Boolean` retain context-key value ownership. |
| IAMCOND-008 | `test_IAMCOND_008_recognized_well_structured_condition_remains_valid_per_family` | `CONFIGURE_IAM_POLICY_RULE_FAMILY`; `VALIDATE_IAM_POLICY_DOCUMENT`; `VALIDATE_SHARED_CONDITION`; `VALIDATE_CONDITION_OPERATOR_BODY` | `policy_identity.json`, `policy_resource.json`, and `policy_resource_ecr.json` retain family statement ownership and refer to `policy#/definitions/Condition`; the three rule classes retain family selection. |
| IAMCOND-009 | `test_IAMCOND_009_supported_intrinsic_in_place_of_condition_operator_is_not_unknown`;<br>`test_IAMCOND_009_supported_intrinsics_keep_existing_embedded_policy_outcomes` | `VALIDATE_IAM_POLICY_DOCUMENT`; `VALIDATE_SHARED_CONDITION`; `VALIDATE_CONDITION_OPERATOR_BODY` | `FunctionFilter` retains whole-value intrinsic delegation; `_keywords_cfn.additionalProperties` retains the top-level member exemption; `Policy.validate` retains object context and disables functions only after JSON-string parsing. |
| IAMCOND-010 | `test_IAMCOND_010_object_and_json_string_representations_have_equivalent_outcomes` | `CONFIGURE_IAM_POLICY_RULE_FAMILY`; `VALIDATE_IAM_POLICY_DOCUMENT` | `Policy.validate` owns object/string normalization once for all families; rule `keywords` and effective provider schemas own entry-point eligibility. |
| IAMCOND-011 | `test_IAMCOND_011_statement_without_optional_condition_has_no_condition_finding` | `VALIDATE_IAM_POLICY_DOCUMENT`; `VALIDATE_SHARED_CONDITION` | Each family statement schema exposes `Condition` in `properties` but omits it from `required`; no new default or invocation hook is introduced. |
| IAMCOND-012 | `test_IAMCOND_012_multiple_operators_and_context_keys_remain_accepted` | `VALIDATE_IAM_POLICY_DOCUMENT`; `VALIDATE_SHARED_CONDITION`; `MATCH_RECOGNIZED_CONDITION_OPERATOR`; `VALIDATE_CONDITION_OPERATOR_BODY` | `patternProperties`, `properties`, and nested `additionalProperties` retain exhaustive per-member descent; no `oneOf`, cardinality constraint, or short-circuiting layer is added. |
| IAMCOND-013 | `test_IAMCOND_013_condition_finding_does_not_suppress_independent_findings`;<br>`test_IAMCOND_013_condition_finding_does_not_suppress_invalid_principal` | `CONFIGURE_IAM_POLICY_RULE_FAMILY`; `VALIDATE_IAM_POLICY_DOCUMENT`; `VALIDATE_SHARED_CONDITION` | Family schemas retain Version, Statement, Effect, Action, Resource, Principal, and unsupported-property contracts; `Policy.validate` retains full `iter_errors` streaming and finding attribution. |

## Issue 122 implementation-ready record

The IAMCOND-001 and IAMCOND-003 flow crosses the following loci. Each row is a
single ownership assignment; no row authorizes a duplicate validator at another
locus.

| Trace | Owner and responsibility | Boundary, dependency, and data contract | Failure and verification seam | Implementation order |
| --- | --- | --- | --- | --- |
| IAMCOND-001, IAMCOND-003; `RESOLVE_ISSUE_122_RULE_SELECTION`; both selection verifications | `ConfigMixIn.include_checks`, consumed by `Runner` and `Rules`, owns additive rule selection. | Incoming CLI/config values are appended after `W` and `E`; `Rules.is_rule_enabled` consumes the resulting prefixes. No template or finding data is mutated at this seam. | Configuration and decode failures remain owned by their existing rules. The Runner selectors compare E3510 path/message/severity signatures with and without `I`. | Preserve this seam unchanged; it already keeps E3510 selected in both modes. |
| IAMCOND-001, IAMCOND-003; `VALIDATE_ISSUE_122_IDENTITY_POLICY_ENTRY_POINTS`; all issue 122 verifications | `IdentityPolicy.keywords` owns E3510 reach, while E1101 owns synchronous keyword delegation from the provider-schema walk. | A decoded resource property path generated by `FunctionFilter` crosses E1101 as a `cfnLint` keyword; exact equality with one of the six E3510 keywords passes the policy value and validator context to `Policy.validate`. E3510 depends on E1101 as a parent; provider schemas do not depend on IAM internals. | A missing registration would remain silent at E3510 and is therefore pinned by the six-entry-point keyword/path matrix. Findings retain the resource-property prefix established by the provider-schema traversal. | Preserve E1101 and provider schemas; use the existing six E3510 keywords. |
| IAMCOND-001, IAMCOND-003; `VALIDATE_IAM_POLICY_DOCUMENT`; ManagedPolicy and six-entry-point verifications | `Policy.validate` owns representation normalization, resolver construction, exhaustive error streaming, and concrete-rule attribution. | Object policies retain the incoming CloudFormation-function context; valid JSON strings become parsed policy data with functions disabled. Both forms flow to `policy_identity.json`, which depends on `policy#/definitions/Condition`. Relative schema errors flow back synchronously and are attributed to E3510 unless an intrinsic or `cfnLint` validator owns them. | Invalid JSON strings keep the established no-IAM-schema-finding behavior. The issue fixtures use object form and require at least one error-level E3510 beneath each concrete Condition prefix. | Preserve normalization and attribution; do not add missing-operator logic to Python. |
| IAMCOND-001, IAMCOND-003; `VALIDATE_SHARED_CONDITION`; `MATCH_RECOGNIZED_CONDITION_OPERATOR`; ManagedPolicy and six-entry-point verifications | `policy.json#/definitions/Condition` owns the operator namespace and `policy_identity.json` owns identity-statement structure. | `policy_identity.json` imports the stable shared `Condition` pointer. Recognized operator names descend to existing body contracts; an unrecognized context key at the operator level is excluded by the closed Condition object. The policy instance remains read-only. | `additionalProperties: false` yields the unknown member path below `Statement/0/Condition`; `Policy.validate` assigns E3510 and the rule metadata supplies error severity. | Correct complete operator patterns first, close only the shared Condition object second, and leave context-key namespaces open inside operator bodies. |
| IAMCOND-001, IAMCOND-003; all five issue 122 procedures; all issue 122 verifications | `test/unit/rules/resources/iam/` owns acceptance fixtures, active Runner contracts, and requirement/logic/architecture traceability. | The exact reproduction and six-resource matrix enter through the public Runner seam. No fixture owns production behavior, and no production package depends on test artifacts. | The selectors pin selection continuity, registration, severity, and full finding prefixes; execution remains owned by the Atlas harness. | Keep the fixtures and focused selectors active alongside the shared schema implementation. |

### E3510 entry-point topology

All six registered paths converge before condition validation. The provider walk
supplies the prefix in the middle column; the shared schema supplies the common
tail in the last column.

| Resource owner | Registered E3510 keyword and concrete fixture prefix | Required finding location |
| --- | --- | --- |
| `AWS::IAM::Group` | `Resources/AWS::IAM::Group/Properties/Policies/*/PolicyDocument` → `Resources/IAMGroup/Properties/Policies/0/PolicyDocument` | prefix + `Statement/0/Condition/servicecatalog:accountLevel` |
| `AWS::IAM::ManagedPolicy` | `Resources/AWS::IAM::ManagedPolicy/Properties/PolicyDocument` → `Resources/IAMManagedPolicy/Properties/PolicyDocument` | prefix + `Statement/0/Condition/servicecatalog:accountLevel` |
| `AWS::IAM::Policy` | `Resources/AWS::IAM::Policy/Properties/PolicyDocument` → `Resources/IAMPolicy/Properties/PolicyDocument` | prefix + `Statement/0/Condition/servicecatalog:accountLevel` |
| `AWS::IAM::Role` | `Resources/AWS::IAM::Role/Properties/Policies/*/PolicyDocument` → `Resources/IAMRole/Properties/Policies/0/PolicyDocument` | prefix + `Statement/0/Condition/servicecatalog:accountLevel` |
| `AWS::IAM::User` | `Resources/AWS::IAM::User/Properties/Policies/*/PolicyDocument` → `Resources/IAMUser/Properties/Policies/0/PolicyDocument` | prefix + `Statement/0/Condition/servicecatalog:accountLevel` |
| `AWS::SSO::PermissionSet` | `Resources/AWS::SSO::PermissionSet/Properties/InlinePolicy` → `Resources/SSOPermissionSet/Properties/InlinePolicy` | prefix + `Statement/0/Condition/servicecatalog:accountLevel` |

The single-resource IAMCOND-001 fixture intentionally uses logical ID
`IAMPolicy` with resource type `AWS::IAM::ManagedPolicy`; its required prefix is
therefore `Resources/IAMPolicy/Properties/PolicyDocument`, independent of the
logical ID used for ManagedPolicy in the six-resource fixture.

## Issue 123 implementation-ready record

The IAMCOND-004 flow crosses the following loci. Each row assigns one cohesive
responsibility and preserves the two issue 123 verification obligations and all
six mapped procedures at their concrete implementation seams.

| Trace | Owner and responsibility | Boundary, dependency, and data contract | Failure, lifecycle, and verification seam | Implementation order |
| --- | --- | --- | --- | --- |
| IAMCOND-004; `VALIDATE_ISSUE_123_RESOURCE_POLICY_ENTRY_POINTS`; both issue 123 verifications | `ResourcePolicy.keywords` owns E3512 reach across KMS, OpenSearch Service, S3, SNS, and SQS; E1101 owns synchronous delegation from the provider-schema walk. | `FunctionFilter` adds the complete resource/property path as a `cfnLint` keyword. E1101 compares it with the five registered strings and passes the policy value plus current validator context to `ResourcePolicy.validate`. E3512 depends on E1101 as a parent; provider schemas remain independent of IAM internals. | Missing registration terminates without E3512 delegation and is pinned by each selector's keyword assertion. Provider traversal supplies the concrete resource-property prefix. Dispatch is stateless and read-only; no queue, event, retry, or recovery state exists. | Preserve the five keyword registrations and provider schemas; no entry-point-specific validator or adapter is introduced. |
| IAMCOND-004; `CONFIGURE_IAM_POLICY_RULE_FAMILY`; `VALIDATE_IAM_POLICY_DOCUMENT`; both issue 123 verifications | `ResourcePolicy.__init__` selects the `resource` family, and `Policy.validate` owns representation normalization, resolver construction, exhaustive error streaming, and E3512 attribution. | Object policies retain the incoming CloudFormation-function context; valid JSON strings are parsed with functions disabled. Both representations flow to `policy_resource.json`. Relative schema errors return synchronously and receive `ResourcePolicy` ownership unless an intrinsic or `cfnLint` validator already owns them. | Decode failure remains owned by the established template/parser path; an invalid JSON policy string returns without an IAM-schema finding. Independent schema errors remain in the stream and cannot suppress a Condition result from the same or a later resource. | Preserve normalization and attribution in `Policy`; missing-operator logic does not belong in Python. |
| IAMCOND-004; `CONFIGURE_IAM_POLICY_RULE_FAMILY`; `VALIDATE_IAM_POLICY_DOCUMENT`; `VALIDATE_SHARED_CONDITION`; both issue 123 verifications | `policy_resource.json` owns resource-policy statement structure and imports `policy#/definitions/Condition`; `policy.json#/definitions/Condition` owns the operator namespace. | The normalized document crosses the family boundary through the stable `policy` schema ID and `Condition` JSON Pointer. `Statement.Condition` remains optional. A present object is read without mutation; its members are matched against explicit properties and fully anchored `patternProperties`. | The family schema continues to require Effect plus the Action, Resource, and Principal choices. Those failures remain independently owned by E3512. The issue fixtures isolate the Condition decision with otherwise valid statements. | Preserve the family `$ref` and constraints; evolve only the shared Condition contract when operator grammar changes. |
| IAMCOND-004; `VALIDATE_SHARED_CONDITION`; `MATCH_RECOGNIZED_CONDITION_OPERATOR`; `VALIDATE_CONDITION_OPERATOR_BODY`; both issue 123 verifications | The shared closed Condition schema and the CloudFormation-aware JSON Schema keyword implementations own classification, descent, and member-relative error paths. | `servicecatalog:accountLevel` matches no recognized operator, so `additionalProperties: false` yields a relative error at `Statement/0/Condition/servicecatalog:accountLevel`. `StringEquals` selects `ConditionValue`, whose open context-key contract accepts `aws:SourceAccount` with its string value and yields no Condition error. `Policy.validate` preserves E3512 ownership on the former. | Malformed input terminates with error-level E3512 at the offending member; recognized nested input terminates without an E3512 finding at or beneath its Condition path. Traversal is synchronous, deterministic, exhaustive, stateless, and read-only; persistence, transactions, events, retries, compensation, and rollback do not apply. | Keep the complete operator patterns in place before closing Condition membership; do not close the nested context-key namespace. |
| IAMCOND-004; all six mapped procedures; both issue 123 verifications | `test/unit/rules/resources/iam/` and the paired good/bad IAM fixture directories own acceptance boundaries and requirement-to-verification-to-logic-to-architecture traceability. | Both five-resource fixtures enter through the public Runner seam. The parametrized keyword/path table is the contract between registration and each concrete prefix; production packages have no dependency on these artifacts. | The active malformed selector pins E3512 identity, error severity, and the offending-member prefix. The active recognized selector pins absence of an E3512 Condition finding. | Preserve both fixtures and active selectors as the focused IAMCOND-004 harness boundary. |

### E3512 entry-point topology

Every registered resource path converges on `policy_resource.json` before shared
Condition validation. The malformed fixture requires the common offending tail;
the recognized fixture requires no E3512 finding at or beneath the Condition
prefix.

| Resource owner | Registered E3512 keyword and concrete fixture prefix | Malformed terminal location | Recognized terminal outcome |
| --- | --- | --- | --- |
| `AWS::KMS::Key` | `Resources/AWS::KMS::Key/Properties/KeyPolicy` → `Resources/KMSKey/Properties/KeyPolicy` | prefix + `Statement/0/Condition/servicecatalog:accountLevel` | No E3512 finding beneath prefix + `Statement/0/Condition` |
| `AWS::OpenSearchService::Domain` | `Resources/AWS::OpenSearchService::Domain/Properties/AccessPolicies` → `Resources/OpenSearchDomain/Properties/AccessPolicies` | prefix + `Statement/0/Condition/servicecatalog:accountLevel` | No E3512 finding beneath prefix + `Statement/0/Condition` |
| `AWS::S3::BucketPolicy` | `Resources/AWS::S3::BucketPolicy/Properties/PolicyDocument` → `Resources/S3BucketPolicy/Properties/PolicyDocument` | prefix + `Statement/0/Condition/servicecatalog:accountLevel` | No E3512 finding beneath prefix + `Statement/0/Condition` |
| `AWS::SNS::TopicPolicy` | `Resources/AWS::SNS::TopicPolicy/Properties/PolicyDocument` → `Resources/SNSTopicPolicy/Properties/PolicyDocument` | prefix + `Statement/0/Condition/servicecatalog:accountLevel` | No E3512 finding beneath prefix + `Statement/0/Condition` |
| `AWS::SQS::QueuePolicy` | `Resources/AWS::SQS::QueuePolicy/Properties/PolicyDocument` → `Resources/SQSQueuePolicy/Properties/PolicyDocument` | prefix + `Statement/0/Condition/servicecatalog:accountLevel` | No E3512 finding beneath prefix + `Statement/0/Condition` |

## Issue 124 implementation-ready record

The IAMCOND-005 flow crosses the following loci. Each row assigns one cohesive
responsibility and preserves both issue 124 verification obligations and all six
mapped procedures at their concrete implementation seams.

| Trace | Owner and responsibility | Boundary, dependency, and data contract | Failure, lifecycle, and verification seam | Implementation order |
| --- | --- | --- | --- | --- |
| IAMCOND-005; `VALIDATE_ISSUE_124_ECR_REPOSITORY_POLICY`; both issue 124 verifications | `ResourceEcrPolicy.keywords` owns E3513 reach for `AWS::ECR::Repository.RepositoryPolicyText`; E1101 owns synchronous delegation from the provider-schema walk. | `FunctionFilter` adds `Resources/AWS::ECR::Repository/Properties/RepositoryPolicyText` as a `cfnLint` keyword. E1101 matches that registered string and passes the policy value plus current validator context to `ResourceEcrPolicy.validate`. E3513 depends on E1101 as a parent; the ECR provider schema remains independent of IAM internals. | An absent property or missing registration terminates without E3513 delegation. The selector pins registration, while provider traversal supplies `Resources/ECRRepository/Properties/RepositoryPolicyText` as the concrete prefix. Dispatch is stateless and read-only. | Preserve the existing keyword, E1101 dispatch, and provider schema; do not introduce an ECR-specific condition validator or provider patch. |
| IAMCOND-005; `CONFIGURE_IAM_POLICY_RULE_FAMILY`; `VALIDATE_IAM_POLICY_DOCUMENT`; both issue 124 verifications | `ResourceEcrPolicy.__init__` selects the `resource` resolver name and `policy_resource_ecr.json`; `Policy.validate` owns object/string normalization, resolver construction, exhaustive error streaming, and E3513 attribution. | Object policies retain the incoming CloudFormation-function context; valid JSON strings are parsed with functions disabled. Both representations enter the ECR family schema, whose relative errors return synchronously and receive `ResourceEcrPolicy` ownership unless an intrinsic or `cfnLint` validator already owns them. | Template decode and provider traversal failures retain their established owners. Invalid JSON strings retain the established no-IAM-schema-finding outcome. Independent ECR policy errors remain in the stream and cannot suppress the Condition finding. | Preserve normalization and finding attribution in `Policy`; no Python implementation delta is required. |
| IAMCOND-005; `CONFIGURE_IAM_POLICY_RULE_FAMILY`; `VALIDATE_IAM_POLICY_DOCUMENT`; `VALIDATE_SHARED_CONDITION`; both issue 124 verifications | `policy_resource_ecr.json` owns ECR statement structure and imports `policy#/definitions/Condition`; `policy.json#/definitions/Condition` owns operator recognition. | The ECR schema requires Effect, an Action/NotAction choice, and a Principal/NotPrincipal choice. It intentionally does not require Resource or NotResource. `Statement.Condition` remains optional, but a present object crosses the stable shared-schema `$ref` without mutation. | Family-specific defects remain E3513 findings independent of Condition classification. The recognized fixture omits Resource and NotResource to pin the ECR-specific acceptance contract, while satisfying every other ECR statement requirement. | Preserve the ECR family schema and its `$ref`; evolve only the shared Condition contract when operator grammar changes. |
| IAMCOND-005; `VALIDATE_SHARED_CONDITION`; `MATCH_RECOGNIZED_CONDITION_OPERATOR`; `VALIDATE_CONDITION_OPERATOR_BODY`; both issue 124 verifications | The shared closed Condition schema and CloudFormation-aware JSON Schema keyword implementations own operator classification, body descent, and member-relative paths. | `servicecatalog:accountLevel` matches no recognized operator, so `additionalProperties: false` produces a relative error at `Statement/0/Condition/servicecatalog:accountLevel`. `StringEquals` selects `ConditionValue`, whose open context-key contract accepts `aws:SourceAccount` and its string value. `Policy.validate` preserves E3513 ownership on the malformed result. | Malformed input terminates with error-level E3513 at the exact offending member. Recognized input terminates with no E3513 finding and an accepted ECR statement. Traversal is synchronous, deterministic, exhaustive, stateless, and read-only; persistence, transactions, events, retries, compensation, rollback, and recovery do not apply. | Keep all recognized operator patterns complete before closing Condition membership; keep nested context-key namespaces open. |
| IAMCOND-005; all six mapped procedures; both issue 124 verifications | `test/unit/rules/resources/iam/` and the paired good/bad IAM fixture directories own acceptance boundaries and requirement-to-verification-to-logic-to-architecture traceability. | Both object-form fixtures enter through the public Runner seam. The contract binds E3513 registration to the concrete prefix and shared Condition tail; production packages have no dependency on test artifacts. | The inert malformed selector pins E3513 identity, error severity, and exact offending-member path. The inert recognized selector pins the absence of all E3513 findings, thereby preserving both Condition acceptance and ECR statement semantics until Malkhut enables execution. | Keep both fixtures and selectors inert during Yesod; Malkhut owns skip removal and executable validation. |

### E3513 entry-point topology

The single registered ECR path converges on `policy_resource_ecr.json` before
shared Condition validation. The ECR family boundary, rather than the shared
schema, owns the statement's optional Resource behavior.

| Resource owner | Registered E3513 keyword and concrete fixture prefix | Malformed terminal location | Recognized terminal outcome |
| --- | --- | --- | --- |
| `AWS::ECR::Repository` | `Resources/AWS::ECR::Repository/Properties/RepositoryPolicyText` → `Resources/ECRRepository/Properties/RepositoryPolicyText` | prefix + `Statement/0/Condition/servicecatalog:accountLevel` | No E3513 findings; `StringEquals` is accepted while Resource and NotResource remain omitted |

## Architectural loci

### Issue 122 selection and entry-point dispatch

- **Requirements:** IAMCOND-001 and IAMCOND-003.
- **Verification:** all selectors in `test_iamcond_issue_122_contract.py`.
- **Procedures:** `RESOLVE_ISSUE_122_RULE_SELECTION` and
  `VALIDATE_ISSUE_122_IDENTITY_POLICY_ENTRY_POINTS`.
- **Owners:** `ConfigMixIn.include_checks`, `Runner`, `Rules`, E1101,
  `IdentityPolicy.keywords`, and effective provider schemas.
- **Incoming dependency:** normal CLI selection or `--include-checks I`, plus a
  decoded template containing one of the six registered identity-policy paths.
- **Outgoing dependency:** E1101 delegates the selected property value to E3510,
  which selects `policy_identity.json` through `Policy.validate`.
- **Contract:** W/E remain active when I is appended; Group, ManagedPolicy,
  Policy, Role, User, and SSO PermissionSet all reach the same identity schema;
  relative schema paths are prefixed with the concrete resource/property path.
- **Failure contract:** decode/configuration failures retain their established
  ownership; malformed Condition members produce error-level E3510 findings;
  informational selection cannot remove or mutate those E3510 signatures.
- **Lifecycle:** dispatch and validation are synchronous, stateless, read-only,
  and exhaustive. No persistence, retry, compensation, or rollback applies.
- **Test seam:** the active Runner-level issue 122 fixtures and selectors
  exercise selection, dispatch, severity, and complete finding paths.

### Shared condition schema

- **Requirements:** IAMCOND-001, IAMCOND-002, IAMCOND-003, IAMCOND-004,
  IAMCOND-005, IAMCOND-006, IAMCOND-007, IAMCOND-008, IAMCOND-009,
  IAMCOND-011, IAMCOND-012, IAMCOND-013.
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
  multiplicity, omission, and independent-finding matrices, plus the issue 122
  through issue 124 missing-operator Runner matrices.
- **Implementation order:** repair full-name patterns, close the Condition
  object, then activate each issue contract in its Malkhut phase.

### Family policy schemas and rule delegates

- **Requirements:** IAMCOND-004, IAMCOND-005, IAMCOND-008, IAMCOND-010, IAMCOND-011,
  IAMCOND-013.
- **Verification:** `test_IAMCOND_004_*`, `test_IAMCOND_005_*`,
  `test_IAMCOND_008_*`, `test_IAMCOND_010_*`, `test_IAMCOND_011_*`, and both
  `test_IAMCOND_013_*` selectors.
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

- **Requirements:** IAMCOND-001, IAMCOND-003, IAMCOND-004, IAMCOND-005,
  IAMCOND-008, IAMCOND-009, IAMCOND-010, IAMCOND-013.
- **Verification:** `test_IAMCOND_004_*`, `test_IAMCOND_005_*`,
  `test_IAMCOND_008_*`, both `test_IAMCOND_009_*`, `test_IAMCOND_010_*`, and
  both `test_IAMCOND_013_*` selectors.
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

- **Requirements:** IAMCOND-001, IAMCOND-003, IAMCOND-004, IAMCOND-005, IAMCOND-010.
- **Verification:**
  `test_IAMCOND_001_managed_policy_missing_operator_reports_error_E3510_at_condition_with_normal_and_information_selection[selection-mode]`,
  both `test_IAMCOND_003_*` selectors, both `test_IAMCOND_004_*` selectors, both
  `test_IAMCOND_005_*` selectors, and
  `test_IAMCOND_010_object_and_json_string_representations_have_equivalent_outcomes`.
- **Procedures:** `RESOLVE_ISSUE_122_RULE_SELECTION`,
  `VALIDATE_ISSUE_122_IDENTITY_POLICY_ENTRY_POINTS`,
  `VALIDATE_ISSUE_123_RESOURCE_POLICY_ENTRY_POINTS`,
  `VALIDATE_ISSUE_124_ECR_REPOSITORY_POLICY`,
  `CONFIGURE_IAM_POLICY_RULE_FAMILY`, and `VALIDATE_IAM_POLICY_DOCUMENT`.
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
  registration and equivalent policy outcomes; the issue 122 matrix asserts all
  six E3510 keyword registrations, while the issue 123 matrices assert all five
  E3512 keyword registrations and concrete Condition path prefixes. The issue
  124 selectors assert E3513 registration, its concrete Condition path, and ECR
  statement acceptance without Resource.
- **Implementation order:** no provider schema or patch edit.

### Verification and traceability artifacts

- **Requirements:** IAMCOND-001, IAMCOND-002, IAMCOND-003, IAMCOND-004,
  IAMCOND-005, IAMCOND-006, IAMCOND-007, IAMCOND-008, IAMCOND-009,
  IAMCOND-010, IAMCOND-011, IAMCOND-012, IAMCOND-013.
- **Verification:** all named selectors in `IAMCOND-VERIFICATION.md`.
- **Procedures:** all nine procedures in `IAMCOND-PSEUDOCODE.md`.
- **Owner:** `test/unit/rules/resources/iam/`.
- **Dependencies:** canonical requirement IDs map forward to verification,
  procedure, and production loci; the reverse map points each verification
  prefix back to its architectural seams.
- **Contract:** the active shared-schema, issue 122, and issue 123 Runner
  matrices and the inert issue 124 Runner selectors are the acceptance
  boundaries for their mapped obligations.
- **Implementation state:** the shared schema implementation is complete. The
  issue 124 skips remain intentionally present until Malkhut; execution remains
  owned by the Atlas harness.

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
