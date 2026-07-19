# Issue 138 IAM Condition Entry-Point Logic

This artifact specifies how E3510 applies the shared corrected IAM Condition
semantics to every identity-policy document it owns. It changes no runtime
behavior by itself and composes with the shared positive and negative Condition
procedures in the Issue 136 and Issue 137 logic artifacts.

## Owned entry-point matrix

The ordered `E3510_IDENTITY_POLICY_PATHS` collection contains exactly these
keyword paths and concrete policy-path shapes:

| Resource type | E3510 keyword path | Concrete policy path below the resource |
| --- | --- | --- |
| `AWS::IAM::Group` | `Resources/AWS::IAM::Group/Properties/Policies/*/PolicyDocument` | `Properties.Policies[index].PolicyDocument` |
| `AWS::IAM::ManagedPolicy` | `Resources/AWS::IAM::ManagedPolicy/Properties/PolicyDocument` | `Properties.PolicyDocument` |
| `AWS::IAM::Policy` | `Resources/AWS::IAM::Policy/Properties/PolicyDocument` | `Properties.PolicyDocument` |
| `AWS::IAM::Role` | `Resources/AWS::IAM::Role/Properties/Policies/*/PolicyDocument` | `Properties.Policies[index].PolicyDocument` |
| `AWS::IAM::User` | `Resources/AWS::IAM::User/Properties/Policies/*/PolicyDocument` | `Properties.Policies[index].PolicyDocument` |
| `AWS::SSO::PermissionSet` | `Resources/AWS::SSO::PermissionSet/Properties/InlinePolicy` | `Properties.InlinePolicy` |

The wildcard is an iteration point, not a single selected element. Each
concrete array index produces its own policy-document invocation and path.

## Procedure: register_e3510_identity_policy_entry_points

```text
PROCEDURE register_e3510_identity_policy_entry_points()
  REQUIREMENT_IDS: IAMCOND-006
  VERIFICATION:
    test_iamcond_006_given_equivalent_valid_corrected_condition_when_each_e3510_owned_resource_type_is_linted_then_no_unsupported_operator_error
    test_iamcond_006_given_group_role_or_user_with_multiple_policy_entries_when_corrected_operator_occurs_at_any_wildcard_location_then_e3510_accepts_that_entry

  PRECONDITIONS
    IdentityPolicy is the owner of rule ID E3510
    Policy accepts an ordered keyword-path collection, a schema identifier, and
      an identity-policy schema filename

  REGISTER ENTRY POINTS
    SET IdentityPolicy.keywords to E3510_IDENTITY_POLICY_PATHS in the matrix's
      declared order
    SET the shared schema identifier to "identity"
    SET the identity-policy schema filename to "policy_identity.json"

  ESTABLISH SHARED DELEGATION
    LOAD policy.json into the resolver store under "policy"
    LOAD policy_identity.json into the resolver store under "identity"
    REQUIRE every selected identity-policy Statement.Condition to resolve
      through policy_identity.json to policy#/definitions/Condition
    THEREFORE apply the same corrected operator recognition and unchanged value
      contracts to every registered entry point

  POSTCONDITIONS
    E3510 owns all six paths in E3510_IDENTITY_POLICY_PATHS
    NO registered path delegates identity-policy validation to another owning
      policy rule
    Group, role, and user wildcard paths select every Policies array index
    Managed policy, standalone inline policy, and permission-set paths each
      select their single document property when present

  ON FAILURE missing_or_extra_entry_point
    REJECT the registration as incomplete or outside IAMCOND-006 scope
  ON FAILURE schema_identity_mismatch
    REJECT the registration because all six paths must use the same identity
      schema and shared Condition definition
END PROCEDURE
```

## Procedure: validate_e3510_owned_policy_document

```text
PROCEDURE validate_e3510_owned_policy_document(
  caller_validator,
  policy_document,
  owning_policy_path
)
  REQUIREMENT_IDS: IAMCOND-006
  VERIFICATION:
    test_iamcond_006_given_equivalent_valid_corrected_condition_when_each_e3510_owned_resource_type_is_linted_then_no_unsupported_operator_error
    test_iamcond_006_given_genuine_condition_violation_at_each_owned_entry_point_when_template_is_linted_then_match_remains_e3510_with_full_owning_policy_path

  PRECONDITIONS
    owning_policy_path identifies one concrete occurrence selected from
      E3510_IDENTITY_POLICY_PATHS and includes any resolved wildcard index
    IdentityPolicy owns E3510 and has initialized the "identity" and "policy"
      resolver entries

  SELECT INPUT REPRESENTATION
    IF caller_validator classifies policy_document as a string
      EVOLVE an IAM validator with CloudFormation functions disabled, the
        identity schema, and the shared resolver
      ATTEMPT to decode policy_document as JSON
      IF JSON decoding fails
        RETURN no match from this procedure, preserving Policy.validate's
          established handling for an undecodable string
      END IF
      SET validation_input to the decoded value
    ELSE
      EVOLVE an IAM validator with the caller's CloudFormation document,
        context, supported functions, identity schema, and shared resolver
      SET validation_input to policy_document without mutation
    END IF

  VALIDATE IDENTITY POLICY
    DELEGATE validation_input to policy_identity.json
    FOR EACH Statement selected by policy_identity.json, in validator order
      IF Statement.Condition exists
        DELEGATE its Condition to the shared procedures
          validate_shared_iam_condition,
          reject_unrecognized_condition_operator, and
          validate_set_qualified_condition_values as applicable
      END IF
    END FOR

  CLASSIFY EACH VALIDATION ERROR
    FOR EACH error emitted by the evolved IAM validator
      IF error.validator starts with "fn_" OR equals "cfnLint"
        PRESERVE the collaborating rule already attached to error
      ELSE
        ATTACH IdentityPolicy rule E3510 to error
      END IF

      SET observable_path to CONCAT(owning_policy_path, error.path)
      YIELD a match with observable_path, error.message, and the classified rule
    END FOR

  TERMINAL STATES
    VALID_CORRECTED_CONDITION:
      YIELD no unsupported-operator match when each corrected operator is
        recognized and its value satisfies the delegated contract
    GENUINE_POLICY_OR_CONDITION_VIOLATION:
      YIELD the existing validation match; for an ordinary identity-policy
        schema violation, retain E3510 and a path containing the resource,
        concrete policy document, Statement, Condition, and invalid member
    VALID_POLICY_WITH_NO_ERRORS:
      RETURN without a match

  ON FAILURE schema_reference_resolution
    PROPAGATE the validator's existing resolution behavior
    DO NOT widen an operator contract or transfer ordinary policy ownership
  ON REPEATED INVOCATION
    REVALIDATE immutable schema and policy inputs
    DO NOT cache, persist, mutate, retry, compensate, roll back, or emit an event
END PROCEDURE
```

## Procedure: validate_all_e3510_identity_policy_entry_points

```text
PROCEDURE validate_all_e3510_identity_policy_entry_points(template)
  REQUIREMENT_IDS: IAMCOND-006
  VERIFICATION:
    test_iamcond_006_given_equivalent_valid_corrected_condition_when_each_e3510_owned_resource_type_is_linted_then_no_unsupported_operator_error
    test_iamcond_006_given_group_role_or_user_with_multiple_policy_entries_when_corrected_operator_occurs_at_any_wildcard_location_then_e3510_accepts_that_entry
    test_iamcond_006_given_genuine_condition_violation_at_each_owned_entry_point_when_template_is_linted_then_match_remains_e3510_with_full_owning_policy_path
    test_iamcond_006_given_one_valid_corrected_condition_per_owned_resource_type_when_all_are_linted_together_then_entry_point_validation_is_independent_and_unchanged

  PRECONDITIONS
    RECEIVE one decoded CloudFormation template
    E3510 is enabled and register_e3510_identity_policy_entry_points has
      established exactly the six owned keyword paths

  SELECT AND VALIDATE RESOURCES
    FOR EACH (logical_id, resource) selected by template-schema traversal, in
      traversal order
      resource_type := resource.Type

      IF resource_type is AWS::IAM::Group, AWS::IAM::Role, or AWS::IAM::User
        policies := resource.Properties.Policies when present
        FOR EACH (index, policy_entry) IN policies, in array index order
          IF policy_entry.PolicyDocument is present
            owning_policy_path := [
              "Resources", logical_id, "Properties", "Policies", index,
              "PolicyDocument"
            ]
            DELEGATE policy_entry.PolicyDocument and owning_policy_path to
              validate_e3510_owned_policy_document
            APPEND every returned match to this template's match collection
          END IF
        END FOR

      ELSE IF resource_type is AWS::IAM::ManagedPolicy OR AWS::IAM::Policy
        IF resource.Properties.PolicyDocument is present
          owning_policy_path := [
            "Resources", logical_id, "Properties", "PolicyDocument"
          ]
          DELEGATE that document and path to
            validate_e3510_owned_policy_document
          APPEND every returned match to this template's match collection
        END IF

      ELSE IF resource_type is AWS::SSO::PermissionSet
        IF resource.Properties.InlinePolicy is present
          owning_policy_path := [
            "Resources", logical_id, "Properties", "InlinePolicy"
          ]
          DELEGATE that document and path to
            validate_e3510_owned_policy_document
          APPEND every returned match to this template's match collection
        END IF
      END IF

      CONTINUE traversal after every accepted document and every emitted match
    END FOR

  INDEPENDENCE AND ORDERING
    VALIDATE every concrete selected policy in its own delegation
    DO NOT share mutable policy state or error state between delegations
    DO NOT stop after the first resource, array entry, corrected operator, or
      validation error
    PRESERVE each concrete logical ID and array index in its match-path prefix

  RETURN the accumulated match collection in established traversal and validator
    order

  TERMINAL STATES
    ALL_SIX_VALID:
      RETURN no E3510 match when one valid corrected condition occurs in each
        owned resource type, whether linted together or separately
    MULTIPLE_WILDCARD_ENTRIES_VALID:
      RETURN no E3510 match for the corrected condition at index 0 or index 1,
        and continue validating every sibling entry
    MIXED_RESULTS:
      RETURN every independently produced match without changing the result of
        any other entry point

  CONCURRENCY AND ASYNCHRONY
    VALIDATION is synchronous, read-only, and observationally independent per
      policy document
    NO parallel coordination, asynchronous completion, retry, persistence,
      compensation, rollback, notification, or downstream event applies

  ON FAILURE one_entry_point_emits_error
    APPEND that entry point's classified match and CONTINUE all remaining
      entry-point traversal
  ON REPEATED INVOCATION
    REPEAT the same path selection and delegation from immutable inputs
    RETURN the same matches for the same template, schemas, context, and enabled
      rule set
END PROCEDURE
```

## Traceability summary

| Requirement | Verification obligation | Procedure coverage |
| --- | --- | --- |
| IAMCOND-006 | `test_iamcond_006_given_equivalent_valid_corrected_condition_when_each_e3510_owned_resource_type_is_linted_then_no_unsupported_operator_error` | `register_e3510_identity_policy_entry_points`; `validate_e3510_owned_policy_document`; `validate_all_e3510_identity_policy_entry_points` |
| IAMCOND-006 | `test_iamcond_006_given_group_role_or_user_with_multiple_policy_entries_when_corrected_operator_occurs_at_any_wildcard_location_then_e3510_accepts_that_entry` | `register_e3510_identity_policy_entry_points`; `validate_all_e3510_identity_policy_entry_points` |
| IAMCOND-006 | `test_iamcond_006_given_genuine_condition_violation_at_each_owned_entry_point_when_template_is_linted_then_match_remains_e3510_with_full_owning_policy_path` | `validate_e3510_owned_policy_document`; `validate_all_e3510_identity_policy_entry_points` |
| IAMCOND-006 | `test_iamcond_006_given_one_valid_corrected_condition_per_owned_resource_type_when_all_are_linted_together_then_entry_point_validation_is_independent_and_unchanged` | `validate_all_e3510_identity_policy_entry_points` |

The procedures introduce no production-source change. Their implementation
seams remain `IdentityPolicy.__init__` for path ownership, `Policy.validate` for
shared identity-policy delegation and error classification, template-schema
traversal for independent invocation, and `BaseJsonSchema` match conversion for
the full owning path.
