# IAMMP-001/IAMMP-002/IAMMP-003/IAMMP-004/IAMMP-005 schema boundary:
# manual.json owns applicability and the resource-specific PolicyDocument maximum.
# Schema validation dispatches that contract to the generic string-length rule,
# which owns compact object measurement and the over-, exact-, and below-limit
# outcomes without depending on this resource package. IAMMP-004 normalization
# therefore remains below the resource schema boundary; no whitespace policy or
# reverse dependency belongs in this package. IAMMP-005 enters through the same
# contract: the supplied reproduction requires no resource-specific validator or
# repair seam; its oversized document flows to the existing E3033 error boundary.
