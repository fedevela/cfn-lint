# Issue 143 Batch compute-environment Type structural procedures

This artifact records the implementation-ready logic that preserves the
resource-level `AWS::Batch::ComputeEnvironment.Properties.Type` structural
contract while its accepted string domain is widened. It does not change
runtime behavior. Structural ownership remains in the provider schema, while
`Properties` delegates the schema keywords to E3003, E3012, and E3030.

```text
PROCEDURE PRESERVE_BATCH_TYPE_STRUCTURAL_SCHEMA_CONTRACT(provider_schema)
  REQUIREMENT_IDS: BATCHTYPE-007, BATCHTYPE-008
  VERIFICATION:
    test_batchtype_007_omitted_resource_type_emits_e3003_at_properties_boundary
    test_batchtype_008_null_resource_type_emits_e3012_string_contract_finding
    test_batchtype_008_non_string_literal_emits_finding_and_is_not_accepted
    test_batchtype_007_008_accepted_string_passes_structure_and_preserves_domain

  PRECONDITIONS
    provider_schema.typeName equals "AWS::Batch::ComputeEnvironment"
    provider_schema contains /properties/Type
    the Batch extension patch is selected from
      extensions/all/aws_batch_computeenvironment

  LOAD
    required_path := /required
    type_contract_path := /properties/Type/type
    accepted_domain_path := /properties/Type/enum
    accepted_domain := ["MANAGED", "UNMANAGED", "managed", "unmanaged"]

  VALIDATE BEFORE DOMAIN CHANGE
    require "Type" occurs exactly once in provider_schema[required_path]
    require provider_schema[type_contract_path] equals "string"
    require every member of accepted_domain to be a distinct string

  APPLY
    add or replace only provider_schema[accepted_domain_path] with
      accepted_domain through the existing Batch-specific JSON Patch operation

  VALIDATE AFTER DOMAIN CHANGE
    require provider_schema[required_path] still contains "Type"
    require provider_schema[type_contract_path] still equals "string"
    require provider_schema[accepted_domain_path] equals accepted_domain

  PRESERVE
    do not remove, replace, or relax required_path
    do not remove, replace, or widen type_contract_path
    do not add null, boolean, number, array, or object members to accepted_domain
    do not normalize or mutate an input resource value
    do not relax the shared Required, Type, Enum, or JSON Schema keyword logic

  PERSIST
    apply provider patches before extension patches for each regional schema
    apply sorted extension patch files within the resource-specific directory
    write the resulting provider schema through the existing schema-maintenance
      flow
    maintenance may process regions concurrently, but each process applies the
      same resource-scoped patch to its own regional schema

  RETURN
    patched provider_schema whose resource-level Type remains required and
      string-declared and whose enum contains only the four accepted strings

  ON FAILURE missing schema path, patch conflict, failed patch test, invalid
      pointer, or other patch exception
    use ProviderSchemaManager behavior: log the classified patch failure,
      perform no retry or compensation, and continue with the schema state
      available to that regional maintenance process

  REPEATED INVOCATION
    replacing accepted_domain_path with the same accepted_domain preserves the
      required and type paths and yields the same structural schema contract
END PROCEDURE

PROCEDURE VALIDATE_BATCH_TYPE_STRUCTURAL_CONTRACT(resource, validation_regions,
    enabled_child_rules)
  REQUIREMENT_IDS: BATCHTYPE-007, BATCHTYPE-008
  VERIFICATION:
    test_batchtype_007_omitted_resource_type_emits_e3003_at_properties_boundary
    test_batchtype_008_null_resource_type_emits_e3012_string_contract_finding
    test_batchtype_008_non_string_literal_emits_finding_and_is_not_accepted
    test_batchtype_007_008_accepted_string_passes_structure_and_preserves_domain

  PRECONDITIONS
    resource is supplied to the Properties entry point
    E3003 Required, E3012 Type, and E3030 Enum are enabled child rules
    the values covered by this procedure are resolved literals

  LOAD
    properties := resource.Properties if present, otherwise empty object
    schema_groups := provider schemas for resource.Type and validation_regions

  DECIDE ENTRY
    IF resource is not an object OR resource.Type is not a string
      terminate Properties validation and emit no finding from this rule
    END IF
    IF resource.Type does not equal "AWS::Batch::ComputeEnvironment"
      terminate this Batch-specific procedure; any validation for another
        resource type remains governed by that resource's provider schema
    END IF
    IF properties is Ref AWS::NoValue
      emit E3012 at ["Properties", "Ref"]
      terminate Properties validation for this resource
    END IF

  FOR EACH schema_group IN schema_groups IN provider-manager order
    create a region validator carrying schema_group.regions
    set its CloudFormation and value paths to the resource Properties boundary
    attach schema_group.provider_schema and enabled_child_rules
    set CloudFormation property validation to existing non-strict scalar mode

    DECIDE REQUIRED PROPERTY
      IF "Type" is absent from properties
        create one required-keyword error with message
          "'Type' is a required property"
        classify the error as E3003
        prepend "Properties" to its empty schema-relative path
        emit the finding at ["Properties"]
        continue validation of any other applicable schema keywords
      ELSE
        required is satisfied; emit no E3003 finding for Type
      END IF

    IF "Type" is present in properties
      value := properties["Type"]
      allowed_values := schema_group.provider_schema at
        /properties/Type/enum
      declared_type := schema_group.provider_schema at
        /properties/Type/type

      DECIDE STRING CONTRACT
        IF value is null
          the non-strict CloudFormation type check still rejects null
          classify its actual JSON type as "null" in the E3012 adapter
          emit E3012 at ["Properties", "Type"] stating that null does not
            satisfy declared_type "string"
        ELSE IF value is an array or object
          the non-strict CloudFormation type check rejects the structural value
          emit E3012 at ["Properties", "Type"] stating that value does not
            satisfy declared_type "string"
        ELSE IF value is a boolean or number
          preserve the shared non-strict scalar conversion behavior: emit no
            E3012 finding solely from the string keyword
          continue to enum validation so the value cannot be accepted
        ELSE
          value is a literal string; emit no E3012 finding
        END IF

      DECIDE ACCEPTED DOMAIN
        IF value exactly equals one member of allowed_values under the shared
            JSON Schema enum comparator
          emit no E3030 finding
        ELSE
          emit E3030 at ["Properties", "Type"] identifying value and
            allowed_values
        END IF

      STRUCTURAL CONSEQUENCES
        null produces E3012 and remains outside allowed_values
        boolean and number literals remain outside allowed_values and therefore
          produce E3030 even though non-strict scalar type conversion applies
        array and object literals produce E3012 and remain outside
          allowed_values
        "MANAGED", "UNMANAGED", "managed", and "unmanaged" satisfy required,
          type, and enum validation
        every other literal string satisfies required and type validation but
          produces E3030, preserving accepted-domain validation
    END IF
  END FOR

  RETURN
    all E3003, E3012, and E3030 findings from each available schema group,
      retaining each group's regions and the schema-relative property path

  ON FAILURE provider schema absent for one region
    skip that unavailable region and continue with the remaining requested
      regions according to ProviderSchemaManager behavior
  ON FAILURE validation mismatch
    classify through the child rule owning the failing keyword, preserve the
      rejected value and path, and do not retry, mutate, persist, or compensate

  CONCURRENCY AND REPEATED INVOCATION
    runtime validation has no asynchronous branch or shared mutation
    repeated validation with the same resource, region schemas, and child-rule
      set emits the same findings in provider-manager traversal order
END PROCEDURE

PROCEDURE VERIFY_BATCH_TYPE_STRUCTURAL_CONTRACT()
  REQUIREMENT_IDS: BATCHTYPE-007, BATCHTYPE-008
  VERIFICATION:
    test_batchtype_007_omitted_resource_type_emits_e3003_at_properties_boundary
    test_batchtype_008_null_resource_type_emits_e3012_string_contract_finding
    test_batchtype_008_non_string_literal_emits_finding_and_is_not_accepted
    test_batchtype_007_008_accepted_string_passes_structure_and_preserves_domain

  PRECONDITIONS
    the implementation phase has preserved "Type" in /required and "string" at
      /properties/Type/type
    the NETZACH module-level skip has been removed by the executable-validation
      phase
    the fixture attaches Required, Type, and Enum to Properties as E3003, E3012,
      and E3030 respectively

  VERIFY test_batchtype_007_omitted_resource_type_emits_e3003_at_properties_boundary
    validate a Batch compute environment with Properties := empty object
    require exactly one E3003 finding
    require its path equals ["Properties"]
    require its message contains "'Type' is a required property"

  VERIFY test_batchtype_008_null_resource_type_emits_e3012_string_contract_finding
    validate a Batch compute environment with Properties.Type := null
    require exactly one E3012 finding
    require its path equals ["Properties", "Type"]
    require its message states null is not of type "string"

  VERIFY test_batchtype_008_non_string_literal_emits_finding_and_is_not_accepted
    FOR EACH value IN [true, 1.5, empty array, empty object]
      validate a Batch compute environment with Properties.Type := value
      retain findings classified as E3012 or E3030
      require at least one retained finding
      require every retained finding path equals ["Properties", "Type"]
    END FOR

  VERIFY test_batchtype_007_008_accepted_string_passes_structure_and_preserves_domain
    FOR EACH value IN ["managed", "MANAGED"]
      validate a Batch compute environment with Properties.Type := value
      require zero findings
    END FOR
    validate a Batch compute environment with Properties.Type := "invalid"
    require exactly one E3030 finding
    require its path equals ["Properties", "Type"]

  RETURN
    success only after every named verification and parameter iteration
      completes

  ON FAILURE any assertion
    report the failing verification name and parameter identity and terminate
      that test case according to ordinary pytest behavior; do not conceal,
      retry, or rewrite the result
END PROCEDURE
```
