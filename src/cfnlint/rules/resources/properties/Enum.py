"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from cfnlint.jsonschema._keywords import enum
from cfnlint.rules import CloudFormationLintRule


class Enum(CloudFormationLintRule):
    """Check if properties have a valid value"""

    id = "E3030"
    shortdesc = "Check if properties have a valid value"
    description = "Check if properties have a valid value in case of an enumator"
    source_url = "https://github.com/aws-cloudformation/cfn-lint/blob/main/docs/cfn-schema-specification.md#enum"
    tags = ["resources", "property", "allowed value"]
    child_rules = {
        "W2030": None,
    }

    # Architecture contract for GUIDs BATCHTYPE-001 through BATCHTYPE-005:
    # - This rule owns the scoped literal-enum exception; schema generation and the
    #   shared jsonschema enum keyword remain unchanged owners of all other enums.
    # - validator.context.path.cfn_path_string is the property-identity input port;
    #   the boundary key is the exact Batch ComputeEnvironment Type generic path.
    # - The scoped branch must rejoin the existing enum(...) dependency for rejected
    #   literals and every non-target property. Function traversal stays upstream of
    #   this keyword, so this seam must not inspect or reinterpret intrinsic objects.
    # - The contract-test module is the downstream verification seam; this class gains
    #   no public helper, adapter, configuration, or cross-rule dependency.
    def enum(self, validator, enums, instance, schema):
        # Scoped Batch compute-environment Type pseudocode contract:
        #
        # INPUT: validation context, schema enum values, and candidate instance.
        # IDENTIFY: inspect the generic CloudFormation path; the exceptional locus is
        # exactly Resources/AWS::Batch::ComputeEnvironment/Properties/Type.
        #
        # GUID: BATCHTYPE-004
        # IF the candidate is a supported intrinsic value, preserve the existing
        # intrinsic-resolution handoff and its validation outcome; STOP this branch.
        #
        # IF the candidate is a literal at the exceptional locus:
        #   GUID: BATCHTYPE-001
        #   IF its case-normalized semantic value equals MANAGED, accept without E3030.
        #   GUID: BATCHTYPE-002
        #   ELSE IF its case-normalized semantic value equals UNMANAGED, accept without
        #   E3030.
        #   GUID: BATCHTYPE-003
        #   ELSE emit the ordinary enum-validation error for the property.
        #
        # GUID: BATCHTYPE-005
        # ELSE delegate to the existing enum validator with the original instance and
        # enum values, preserving case-sensitive behavior at every other locus.
        if (
            len(validator.context.path.value_path) > 0
            and validator.context.path.value_path[0] == "Parameters"
        ):
            if self.child_rules.get("W2030"):
                yield from self.child_rules["W2030"].enum(
                    validator, enums, instance, schema
                )
            return
        yield from enum(validator, enums, instance, schema)
