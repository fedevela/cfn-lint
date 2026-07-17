# IAMMP-001 schema boundary:
# manual.json owns the resource-specific PolicyDocument maxLength contract.
# Schema validation dispatches that contract to the generic string-length rule;
# the rule must not depend on this resource package.
