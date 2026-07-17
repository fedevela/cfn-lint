# IAMMP-001/IAMMP-002/IAMMP-003 schema boundary:
# manual.json owns applicability and the resource-specific PolicyDocument maximum.
# Schema validation dispatches that contract to the generic string-length rule,
# which owns the over-, exact-, and below-limit outcomes without depending on
# this resource package.
