# Issue 144 Batch compute-environment Type outcome procedures

This artifact records the implementation-ready logic that exposes the
`AWS::Batch::ComputeEnvironment.Properties.Type` acceptance contract
consistently across supported schema regions, the CLI and Python API, and JSON
and YAML representations. It does not change runtime behavior. Runtime
ownership remains distributed across the decoder dispatcher, runner, provider
schema manager, `Properties` rule, E3030 enum rule, and JSON formatter.

```text
PROCEDURE GROUP_SUPPORTED_BATCH_SCHEMA_REGIONS(requested_regions)
  REQUIREMENT_IDS: BATCHTYPE-004
  VERIFICATION:
    test_batchtype_004_every_supported_region_including_cached_primary_accepts_all_four_resource_type_spellings
    test_batchtype_004_every_supported_region_rejects_invalid_value_at_resource_type_path

  PRECONDITIONS
    requested_regions is ordered according to the caller's selected REGIONS
    resource_type := "AWS::Batch::ComputeEnvironment"
    REGION_PRIMARY := "us-east-1"
    ProviderSchemaManager caches are available for read-only runtime lookup

  DISCOVER
    supported_regions := empty ordered list
    FOR EACH region IN requested_regions IN caller order
      region_resource_types := ProviderSchemaManager.get_resource_types(region)
      IF resource_type occurs in region_resource_types
        append region to supported_regions
      END IF
    END FOR

  GROUP
    cached_regions := empty ordered list
    cached_schema := absent
    schema_groups := empty ordered list

    FOR EACH region IN supported_regions IN caller order
      ATTEMPT schema := ProviderSchemaManager.get_resource_schema(
        region, resource_type)

      IF resource_type is unavailable in region
        skip region without retry, fallback finding, or synthetic schema
        continue with the next region
      ELSE IF schema.is_cached is false AND region differs from REGION_PRIMARY
        append ([region], schema) to schema_groups immediately
      ELSE
        append region to cached_regions
        cached_schema := schema
      END IF
    END FOR

    IF cached_schema is present
      append (cached_regions, cached_schema) to schema_groups
    END IF

  CACHE RESOLUTION
    IF a regional provider module lists the Batch schema as cached
      load the REGION_PRIMARY Batch schema
      copy its Schema wrapper
      set copied_schema.is_cached := true
      cache copied_schema under that requested region
      return copied_schema for the regional lookup
    ELSE
      load and cache that region's materialized Batch provider schema
    END IF

  VALIDATE GROUP INVARIANTS
    grouped_regions := every region from schema_groups, flattened in group order
    require grouped_regions contains every supported region exactly once
    require REGION_PRIMARY occurs in grouped_regions
    require at least one supported region resolves through a cached schema
    require every cached supported region belongs to the group containing
      REGION_PRIMARY

  RETURN
    supported_regions and schema_groups, retaining requested-region order and
      singleton direct-schema groups before the final primary/cached group

  ON FAILURE unsupported requested region
    TemplateRunner rejects the configuration with InvalidRegionException before
      rule execution; no Batch outcome is produced for that invocation
  ON FAILURE provider module import or schema load cannot supply resource_type
    classify lookup as ResourceNotFoundError, omit that region from schema_groups,
      and continue with remaining requested regions

  CONCURRENCY AND REPEATED INVOCATION
    runtime grouping is synchronous and mutates only manager lookup caches
    cache population does not alter schema content or group membership
    repeated calls with the same manager state and ordered regions produce the
      same groups and terminal result
END PROCEDURE

PROCEDURE VALIDATE_RESOURCE_LEVEL_BATCH_TYPE(template, validation_regions)
  REQUIREMENT_IDS: BATCHTYPE-004, BATCHTYPE-009, BATCHTYPE-011
  VERIFICATION:
    test_batchtype_004_every_supported_region_including_cached_primary_accepts_all_four_resource_type_spellings
    test_batchtype_004_every_supported_region_rejects_invalid_value_at_resource_type_path
    test_batchtype_009_cli_and_python_api_agree_on_resource_type_acceptance_or_rejection
    test_batchtype_011_equivalent_json_and_yaml_have_identical_resource_type_rule_ids_and_outcomes
    test_batchtype_009_011_invalid_cli_api_json_yaml_findings_identify_resource_type_not_nested_type

  PRECONDITIONS
    template is a decoded CloudFormation object
    template.Resources.BatchEnvironment.Type equals
      "AWS::Batch::ComputeEnvironment"
    template.Resources.BatchEnvironment.Properties.Type is a resolved string
    E3030 Enum is enabled as the child rule for the enum keyword
    accepted_resource_types :=
      ["MANAGED", "UNMANAGED", "managed", "unmanaged"]

  LOAD
    resource := template.Resources.BatchEnvironment
    candidate := resource.Properties.Type
    schema_groups := GROUP_SUPPORTED_BATCH_SCHEMA_REGIONS(validation_regions)
    findings := empty ordered list

  FOR EACH (group_regions, provider_schema) IN schema_groups IN manager order
    create a region validator carrying group_regions
    set its CloudFormation and value path at
      ["Resources", "BatchEnvironment", "Properties"]
    attach provider_schema and the configured Properties child rules
    allowed_values := provider_schema at /properties/Type/enum

    DECIDE RESOURCE-LEVEL TYPE
      IF candidate exactly equals one member of allowed_values under the shared
          JSON Schema enum comparator
        emit no E3030 finding for candidate in group_regions
      ELSE
        create one enum validation error identifying candidate and allowed_values
        classify it through the Properties enum mapping as E3030
        prepend "Properties" to the schema-relative path ["Type"]
        materialize the full match path as
          ["Resources", "BatchEnvironment", "Properties", "Type"]
        append the match to findings with group_regions retained in context
      END IF

    PRESERVE PATH SEPARATION
      do not read /definitions/ComputeResources/properties/Type/enum when
        validating resource.Properties.Type
      do not report ["Resources", "BatchEnvironment", "Properties",
        "ComputeResources", "Type"] for a resource-level candidate
  END FOR

  OUTCOME
    IF candidate is one of accepted_resource_types
      require findings contains no resource-level E3030 match
    ELSE IF candidate equals "invalid"
      require every applicable schema group emits resource-level E3030
    ELSE
      preserve ordinary exact enum behavior for the candidate
    END IF

  RETURN
    findings without normalizing or mutating candidate, template, or schemas

  ON FAILURE transform produces findings
    return enabled transform findings and terminate rule validation
  ON FAILURE rule raises an unexpected exception
    preserve Rules behavior: expose the enabled rule-error finding and do not
      translate it into E3030
  ON FAILURE enum mismatch
    expose E3030 at the resource-level Type path; do not retry, compensate,
      persist, or inspect the nested Type domain

  CONCURRENCY AND REPEATED INVOCATION
    validation is synchronous and has no shared template or schema mutation
    TemplateRunner deduplicates equal matches before returning them
    repeated validation of equal templates, regions, schemas, and rules produces
      the same resource-level rule identifiers and paths
END PROCEDURE

PROCEDURE DECODE_EQUIVALENT_BATCH_TEMPLATE(payload, payload_source)
  REQUIREMENT_IDS: BATCHTYPE-011
  VERIFICATION:
    test_batchtype_011_equivalent_json_and_yaml_have_identical_resource_type_rule_ids_and_outcomes
    test_batchtype_009_011_invalid_cli_api_json_yaml_findings_identify_resource_type_not_nested_type

  PRECONDITIONS
    payload_source is either an in-memory string or a CLI filename/stdin source
    payload encodes one JSON or YAML CloudFormation representation
    equivalent representations contain the same resource keys and Type value

  RECEIVE
    IF payload_source is an in-memory API string
      payload_value := payload
      yaml_decoder := cfn_yaml.loads
      json_fallback_decoder := cfn_json.loads
      filename := absent
    ELSE
      payload_value := payload_source
      yaml_decoder := cfn_yaml.load
      json_fallback_decoder := cfn_json.load
      filename := payload_source
    END IF

  DECODE
    ATTEMPT template := yaml_decoder(payload_value)
    IF the YAML scanner rejects a condition eligible for JSON fallback
      ATTEMPT template := json_fallback_decoder(payload_value)
    END IF

  NORMAL SUCCESS
    require template is an object
    preserve key names and scalar string values exactly
    preserve source marks for location reporting without making marks part of
      enum membership, rule identity, or logical match path
    note that JSON text is YAML-compatible and ordinarily succeeds through the
      first marked YAML decoder; parity depends on semantic content, not on a
      forced parser selection by filename extension

  RETURN
    decoded template and an empty parse-finding list

  ON FAILURE file access, Unicode decoding, YAML construction, YAML scanning,
      JSON fallback, or non-object template
    return no lintable template plus the existing E0000 parse/file findings
    terminate downstream Batch validation for that execution
    do not retry beyond the existing eligible JSON fallback and do not translate
      a parse failure into E3030

  REPEATED INVOCATION
    decoding performs no persistence or asynchronous work
    equivalent JSON and YAML representations may carry different source marks
      but yield equal semantic resource keys and Type string values
END PROCEDURE

PROCEDURE EXPOSE_BATCH_TYPE_OUTCOME(interface, payload, region, format)
  REQUIREMENT_IDS: BATCHTYPE-009, BATCHTYPE-011
  VERIFICATION:
    test_batchtype_009_cli_and_python_api_agree_on_resource_type_acceptance_or_rejection
    test_batchtype_011_equivalent_json_and_yaml_have_identical_resource_type_rule_ids_and_outcomes
    test_batchtype_009_011_invalid_cli_api_json_yaml_findings_identify_resource_type_not_nested_type

  PRECONDITIONS
    interface is CLI or PYTHON_API
    format is json or yaml
    region is identical for compared executions
    payload representations are semantically equivalent

  DECIDE ENTRY SURFACE
    IF interface equals PYTHON_API
      (template, decode_findings) :=
        DECODE_EQUIVALENT_BATCH_TEMPLATE(payload, in-memory API string)
      config := ConfigMixIn from ManualArgs(regions=[region])
      IF decode_findings is non-empty OR template is absent
        return decode_findings
      END IF
      runner := Runner(config)
      matches := all results from runner.validate_template(absent, template)
    ELSE IF interface equals CLI
      persist payload only in the caller-selected temporary template file
      parse CLI arguments --format json --regions region -- template_file
      config := ConfigMixIn(parsed CLI arguments)
      runner := Runner(config)
      (template, decode_findings) :=
        DECODE_EQUIVALENT_BATCH_TEMPLATE(template_file, CLI filename)
      IF decode_findings is non-empty OR template is absent
        matches := decode_findings
      ELSE
        matches := all results from runner.validate_template(template_file,
          template)
      END IF
      sort matches by filename, line number, and rule identifier
      serialize matches through JsonFormatter, including Rule.Id and
        Location.Path
      choose the existing bitwise CLI exit status from emitted severities;
        an E3030 may produce a nonzero process result without invalidating its
        JSON stdout outcome
    ELSE
      reject the unsupported interface before decode or validation
    END IF

  SHARED DELEGATION
    both valid surfaces delegate to TemplateRunner with equivalent region
      configuration and the ordinary loaded rule collection
    TemplateRunner rejects unsupported regions, transforms the template, runs
      rules, applies metadata directives, and deduplicates matches
    Properties delegates resource-level enum validation to
      VALIDATE_RESOURCE_LEVEL_BATCH_TYPE(template, [region])

  OBSERVE
    e3030_outcome := ordered pairs of
      (match.Rule.Id, match.Location.Path) for matches whose Rule.Id is "E3030"
    IF candidate is "MANAGED", "UNMANAGED", "managed", or "unmanaged"
      e3030_outcome := empty list
    ELSE IF candidate equals "invalid"
      e3030_outcome := [("E3030",
        ["Resources", "BatchEnvironment", "Properties", "Type"])]
    END IF

  RETURN
    e3030_outcome in the surface's native representation

  ON FAILURE invalid region
    expose InvalidRegionException through the surface's existing error behavior;
      do not manufacture an acceptance or rejection outcome
  ON FAILURE decode or transform
    expose the existing parse or transform findings and terminate E3030
      comparison because no resource-level enum outcome exists
  ON FAILURE CLI subprocess exits nonzero after emitting JSON findings
    retain and inspect stdout because check is intentionally false; do not retry

  CONCURRENCY AND REPEATED INVOCATION
    API and CLI validation are synchronous; the verification subprocess is
      awaited before its stdout is decoded
    temporary-file persistence belongs only to the verification caller and does
      not alter the template or provider schema
    repeated executions with equal payload semantics, rules, and region yield
      equal E3030 rule identifiers and logical paths
END PROCEDURE

PROCEDURE VERIFY_BATCH_TYPE_OUTCOME_CONSISTENCY()
  REQUIREMENT_IDS: BATCHTYPE-004, BATCHTYPE-009, BATCHTYPE-011
  VERIFICATION:
    test_batchtype_004_every_supported_region_including_cached_primary_accepts_all_four_resource_type_spellings
    test_batchtype_004_every_supported_region_rejects_invalid_value_at_resource_type_path
    test_batchtype_009_cli_and_python_api_agree_on_resource_type_acceptance_or_rejection
    test_batchtype_011_equivalent_json_and_yaml_have_identical_resource_type_rule_ids_and_outcomes
    test_batchtype_009_011_invalid_cli_api_json_yaml_findings_identify_resource_type_not_nested_type

  PRECONDITIONS
    the Batch resource-level enum is
      ["MANAGED", "UNMANAGED", "managed", "unmanaged"] in every applicable
      direct schema and in the primary schema used by cached regions
    the NETZACH module-level skip has been removed by the executable-validation
      phase
    RESOURCE_TYPE_PATH :=
      ["Resources", "BatchEnvironment", "Properties", "Type"]

  VERIFY test_batchtype_004_every_supported_region_including_cached_primary_accepts_all_four_resource_type_spellings
    discover every REGIONS member whose provider module exposes
      "AWS::Batch::ComputeEnvironment"
    group those regions and require complete, unique coverage, primary presence,
      cached-region presence, and cached membership in the primary group
    FOR EACH supported region
      FOR EACH value IN ["managed", "unmanaged", "MANAGED", "UNMANAGED"]
        lint the YAML representation through the Python API for that region
        require zero E3030 findings
      END FOR
    END FOR

  VERIFY test_batchtype_004_every_supported_region_rejects_invalid_value_at_resource_type_path
    repeat the same supported-region discovery and grouping assertions
    FOR EACH supported region
      lint resource-level Type := "invalid" through the Python API
      require exactly [("E3030", RESOURCE_TYPE_PATH)]
    END FOR

  VERIFY test_batchtype_009_cli_and_python_api_agree_on_resource_type_acceptance_or_rejection
    FOR EACH value IN ["managed", "unmanaged", "MANAGED", "UNMANAGED",
        "invalid"]
      encode the same YAML Batch template for REGION_PRIMARY
      collect CLI and Python API E3030 outcomes
      require both outcome lists are equal
      require an outcome exists exactly when value equals "invalid"
    END FOR

  VERIFY test_batchtype_011_equivalent_json_and_yaml_have_identical_resource_type_rule_ids_and_outcomes
    FOR EACH value IN ["managed", "unmanaged", "MANAGED", "UNMANAGED",
        "invalid"]
      encode semantically equivalent JSON and YAML API strings
      lint both in REGION_PRIMARY
      require the E3030 (rule identifier, path) lists are equal
      require rule identifiers are ["E3030"] exactly for "invalid" and are
        otherwise empty
    END FOR

  VERIFY test_batchtype_009_011_invalid_cli_api_json_yaml_findings_identify_resource_type_not_nested_type
    execute invalid resource-level Type through CLI JSON, CLI YAML, API JSON,
      and API YAML in REGION_PRIMARY
    require every execution equals [("E3030", RESOURCE_TYPE_PATH)]
    require "ComputeResources" does not occur in the observed API path

  RETURN
    success only after every named verification and parameter iteration completes

  ON FAILURE grouping invariant, surface comparison, format comparison, rule
      identifier, path, or outcome assertion
    report the failing verification name and parameter identity and terminate
      that test case according to ordinary pytest behavior
    do not conceal, retry, normalize, or rewrite the observed result
END PROCEDURE
```
