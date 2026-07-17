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
        # GUID: BATCHTYPE-004
        if (
            len(validator.context.path.value_path) > 0
            and validator.context.path.value_path[0] == "Parameters"
        ):
            if self.child_rules.get("W2030"):
                yield from self.child_rules["W2030"].enum(
                    validator, enums, instance, schema
                )
            return

        if (
            validator.context.path.cfn_path_string
            == "Resources/AWS::Batch::ComputeEnvironment/Properties/Type"
            and isinstance(instance, str)
        ):
            normalized_instance = instance.upper()
            # GUID: BATCHTYPE-001
            if normalized_instance == "MANAGED":
                return
            # GUID: BATCHTYPE-002
            if normalized_instance == "UNMANAGED":
                return

        # GUID: BATCHTYPE-003, BATCHTYPE-005
        yield from enum(validator, enums, instance, schema)
