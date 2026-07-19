# Issue 142 Batch compute-environment Type procedures

This artifact describes the implementation-ready logic for the isolated
`AWS::Batch::ComputeEnvironment.Properties.Type` acceptance domain. It does
not change runtime behavior. The owning implementation locus is
`src/cfnlint/data/schemas/patches/extensions/all/aws_batch_computeenvironment/boto.json`;
the shared enum implementation in
`src/cfnlint/rules/resources/properties/Enum.py` and
`src/cfnlint/jsonschema/_keywords.py` remains unchanged.

```text
PROCEDURE APPLY_BATCH_COMPUTE_ENVIRONMENT_TYPE_SCHEMA_PATCH(provider_schema)
  REQUIREMENT_IDS: BATCHTYPE-001, BATCHTYPE-002, BATCHTYPE-003,
                   BATCHTYPE-005, BATCHTYPE-006
  VERIFICATION:
    test_batchtype_001_lowercase_resource_type_is_accepted
    test_batchtype_002_uppercase_resource_type_remains_accepted
    test_batchtype_003_unrelated_resource_type_is_rejected
    test_batchtype_005_lowercase_unrelated_enum_remains_rejected
    test_batchtype_006_each_nested_compute_resources_type_is_accepted
    test_batchtype_006_nested_type_case_drift_and_unrelated_values_are_rejected

  PRECONDITIONS
    provider_schema.typeName equals "AWS::Batch::ComputeEnvironment"
    provider_schema contains /properties/Type
    the all-region extension patch is selected only from the directory for
      aws_batch_computeenvironment

  LOAD
    resource_type_path := /properties/Type/enum
    resource_type_domain := ["MANAGED", "UNMANAGED", "managed", "unmanaged"]
    nested_type_path := /definitions/ComputeResources/properties/Type/enum
    nested_type_domain := ["EC2", "FARGATE", "FARGATE_SPOT", "SPOT"]

  VALIDATE
    require every member of resource_type_domain to be a distinct string
    require every member of nested_type_domain to remain a distinct string

  DECIDE
    IF the selected provider schema is the Batch compute-environment schema
      apply one JSON Patch operation at resource_type_path whose value is
        exactly resource_type_domain
    ELSE
      do not apply this patch
    END IF

  PRESERVE
    do not add lowercase aliases to nested_type_path
    do not modify any other enum in the Batch schema
    do not modify Enum.enum or the shared jsonschema enum comparator
    do not normalize, uppercase, lowercase, or case-fold an input value

  PERSIST
    during schema generation, write the patched schema using the existing
      sorted patch-file order and existing region generation flow
    repeated application produces the same resource_type_domain because the
      JSON object member at resource_type_path is replaced with the same value

  RETURN
    provider_schema with only the resource-level Type acceptance domain widened

  ON FAILURE missing resource_type_path or invalid JSON Patch
    use the existing schema-manager behavior: log the patch failure, perform no
      retry or compensation, and continue with the schema state available to
      the generator
END PROCEDURE

PROCEDURE VALIDATE_RESOURCE_ENUM_DOMAINS(resource, validation_regions)
  REQUIREMENT_IDS: BATCHTYPE-001, BATCHTYPE-002, BATCHTYPE-003,
                   BATCHTYPE-005, BATCHTYPE-006
  VERIFICATION:
    test_batchtype_001_lowercase_resource_type_is_accepted
    test_batchtype_002_uppercase_resource_type_remains_accepted
    test_batchtype_003_unrelated_resource_type_is_rejected
    test_batchtype_005_lowercase_unrelated_enum_remains_rejected
    test_batchtype_006_each_nested_compute_resources_type_is_accepted
    test_batchtype_006_nested_type_case_drift_and_unrelated_values_are_rejected

  PRECONDITIONS
    resource is an object
    resource.Type is a string
    E3030 is enabled as the child rule for the enum keyword
    each value considered by this contract is a resolved literal string

  LOAD
    properties := resource.Properties, defaulting to an empty object
    schema_groups := provider schemas for resource.Type and validation_regions

  DECIDE
    IF properties is Ref AWS::NoValue
      emit the existing E3012 type finding at ["Properties", "Ref"]
      terminate validation for this resource
    END IF

  FOR EACH schema_group IN schema_groups IN provider-manager order
    create a region validator carrying schema_group.regions
    set its value path to the resource Properties path
    attach the schema-group provider schema and configured child rules

    FOR EACH concrete property value with an enum keyword
      allowed_values := the enum at that exact schema location

      IF the concrete value exactly equals any allowed value
        emit no E3030 finding for that property
      ELSE
        create one E3030 validation error identifying the concrete value and
          allowed_values
        prepend "Properties" to the error path
        emit the finding without changing any resource or schema value
      END IF
    END FOR
  END FOR

  DOMAIN CONSEQUENCES
    IF resource.Type equals "AWS::Batch::ComputeEnvironment"
      Properties.Type accepts exactly
        ["MANAGED", "UNMANAGED", "managed", "unmanaged"]
      Properties.ComputeResources.Type independently accepts exactly
        ["EC2", "FARGATE", "FARGATE_SPOT", "SPOT"]
    ELSE
      every enum uses its own schema domain with existing exact comparison;
        for example AWS::Lambda::Function Properties.PackageType rejects "zip"
        because its domain is ["Image", "Zip"]
    END IF

  RETURN
    all findings emitted by the applicable region schema groups

  ON FAILURE provider schema absent for one region
    preserve provider-manager behavior: skip that unavailable region and
      continue with other requested regions
  ON FAILURE enum mismatch
    classify as E3030, preserve the exact property path and rejected value, and
      do not retry, normalize, mutate, persist, or compensate

  CONCURRENCY AND REPEATED INVOCATION
    validation has no asynchronous branch or shared mutation
    repeated validation of the same resource, schemas, regions, and rule set
      yields the same findings in the same traversal order
END PROCEDURE

PROCEDURE VERIFY_BATCH_TYPE_REGRESSION_CONTRACT()
  REQUIREMENT_IDS: BATCHTYPE-001, BATCHTYPE-002, BATCHTYPE-003,
                   BATCHTYPE-005, BATCHTYPE-006, BATCHTYPE-013
  VERIFICATION:
    test_batchtype_001_lowercase_resource_type_is_accepted
    test_batchtype_002_uppercase_resource_type_remains_accepted
    test_batchtype_003_unrelated_resource_type_is_rejected
    test_batchtype_005_lowercase_unrelated_enum_remains_rejected
    test_batchtype_006_each_nested_compute_resources_type_is_accepted
    test_batchtype_006_nested_type_case_drift_and_unrelated_values_are_rejected

  PRECONDITIONS
    the implementation phase has installed resource_type_domain through the
      Batch-specific schema patch
    the NETZACH module-level skip has been removed
    Properties has an E3030 Enum child rule

  FOR EACH value IN ["managed", "unmanaged"]
    validate a Batch compute environment with Properties.Type := value
    require zero E3030 findings
  END FOR

  FOR EACH value IN ["MANAGED", "UNMANAGED"]
    validate a Batch compute environment with Properties.Type := value
    require zero E3030 findings
  END FOR

  validate a Batch compute environment with Properties.Type := "invalid"
  require exactly one E3030 finding at ["Properties", "Type"]
  require the finding message to identify "invalid"

  validate a Lambda function with Properties.PackageType := "zip"
  require exactly one E3030 finding at ["Properties", "PackageType"]
  require the finding message to identify "zip"

  FOR EACH value IN ["EC2", "FARGATE", "FARGATE_SPOT", "SPOT"]
    validate an otherwise valid Batch compute environment with
      Properties.ComputeResources.Type := value
    require zero E3030 findings
  END FOR

  FOR EACH value IN ["ec2", "invalid"]
    validate an otherwise valid Batch compute environment with
      Properties.ComputeResources.Type := value
    require exactly one E3030 finding at
      ["Properties", "ComputeResources", "Type"]
    require the finding message to identify value
  END FOR

  RETURN
    success only after every iteration and assertion completes

  ON FAILURE any assertion
    report the failing verification name and terminate that test case according
      to ordinary pytest behavior; do not conceal, retry, or rewrite the result
END PROCEDURE
```

