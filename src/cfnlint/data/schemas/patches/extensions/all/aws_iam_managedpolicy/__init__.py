# IAMMP-001/IAMMP-002 schema boundary:
# manual.json owns the resource-specific, inclusive PolicyDocument maxLength contract.
# Schema validation dispatches that contract to the generic string-length rule;
# the rule must not depend on this resource package.
