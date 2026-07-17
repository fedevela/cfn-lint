"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from __future__ import annotations

from collections import deque
from typing import AbstractSet, Any, Mapping

from cfnlint.jsonschema import ValidationError, ValidationResult, Validator
from cfnlint.rules.jsonschema.CfnLintKeyword import CfnLintKeyword


class SnapStartSupported(CfnLintKeyword):
    """Check if Lambda function using SnapStart has the correct runtimes"""

    # SNAPSTART-001, SNAPSTART-002, SNAPSTART-003, SNAPSTART-004, SNAPSTART-005,
    # SNAPSTART-008:
    # E2530 owns the private runtime/region capability boundary. Exact runtime keys
    # are the opt-in contract; adding one key must not widen neighboring runtimes.
    # Implementations populate this contract from AWS regional-availability data;
    # callers must not supply capability data. Runtimes absent from this mapping
    # remain owned by the legacy rejection boundary below. Java support is not a
    # capability-map concern and must not acquire a dependency on this mapping.
    _runtime_region_support: Mapping[str, AbstractSet[str]] = {
        "python3.12": frozenset(
            {
                "ap-northeast-1",
                "ap-southeast-1",
                "ap-southeast-2",
                "eu-central-1",
                "eu-north-1",
                "eu-west-1",
                "us-east-1",
                "us-east-2",
                "us-west-2",
            }
        )
    }

    id = "E2530"
    shortdesc = "SnapStart supports the configured runtime"
    description = (
        "To properly leverage SnapStart, you must have a runtime of Java11 or greater"
    )
    source_url = "https://docs.aws.amazon.com/lambda/latest/dg/snapstart.html"
    tags = ["resources", "lambda"]

    def __init__(self):
        super().__init__(["Resources/AWS::Lambda::Function/Properties"])
        self.child_rules = {"I2530": None}
        # SNAPSTART-005 ownership boundary: this typed legacy region contract is
        # the regional authority for Java SnapStart. Runtime-specific capability
        # data may neither replace nor narrow it.
        self.regions: list[str] = [
            "us-east-2",
            "us-east-1",
            "us-west-1",
            "us-west-2",
            "af-south-1",
            "ap-east-1",
            "ap-southeast-3",
            "ap-south-1",
            "ap-northeast-2",
            "ap-northeast-3",
            "ap-southeast-1",
            "ap-southeast-2",
            "ap-northeast-1",
            "ca-central-1",
            "eu-central-1",
            "eu-west-1",
            "eu-west-2",
            "eu-south-1",
            "eu-west-3",
            "eu-north-1",
            "me-south-1",
            "sa-east-1",
        ]

    def validate(
        self, validator: Validator, _, instance: Any, schema: dict[str, Any]
    ) -> ValidationResult:

        for scenario in validator.cfn.get_object_without_conditions(
            instance,
            ["Runtime", "SnapStart"],
        ):
            props = scenario.get("Object")

            runtime = props.get("Runtime")
            snap_start = props.get("SnapStart")
            if not snap_start:
                if self.child_rules["I2530"]:
                    if all(
                        region in self.regions for region in validator.context.regions
                    ):
                        yield from self.child_rules["I2530"].validate(  # type: ignore
                            runtime,
                        )
                continue

            if snap_start.get("ApplyOn") != "PublishedVersions":
                continue

            # SNAPSTART-009 integration boundary: Context owns explicit and implicit
            # region selection. Runtime capability checks consume context.regions at
            # this existing seam and must not introduce a second defaulting path.

            # SNAPSTART-007 architecture boundary: this Lambda-properties validator
            # is the shared E2530 port for direct and SAM-transformed templates.
            # Its contract admits resolved properties plus Context-owned regions,
            # never template-origin metadata. E2530 alone owns the resulting
            # supported-region acceptance or unsupported-region diagnostic.

            # SNAPSTART-007 logic obligation: preserve validation-path parity.
            # INPUT: resolved AWS::Lambda::Function properties and the selected
            # regions, whether linting began with CloudFormation or transformed SAM.
            # FLOW:
            # 1. Converge both entry paths on this E2530 evaluator; do not branch on
            #    template origin or caller identity.
            # 2. Apply the same exact-runtime dispatch and per-region capability
            #    comparison to each equivalent resolved configuration.
            # 3. For supported regions, finish without an E2530 diagnostic.
            # 4. For unsupported regions, hand the same ordered unsupported-region
            #    set to the existing E2530 ValidationError path below.
            # OUTPUT: direct cfn-lint and sam validate --lint yield equal E2530
            # results for equal resolved properties and region selections.
            # FAILURE: unresolved or non-equivalent inputs retain their existing
            # condition-resolution and transform-error paths outside this parity.

            # SNAPSTART-003 logic obligation: preserve an exact runtime boundary.
            # INPUT: the resolved runtime and every region selected by the context.
            # DECISION: enter a Python capability path only when the canonical runtime
            # exactly matches a key in _runtime_region_support; never infer support
            # from a "python" prefix, runtime family, or neighboring version.
            # TRANSITION: an unmatched Python runtime falls through to the existing
            # generic runtime checks, where an enabled SnapStart configuration emits
            # E2530 through the unsupported-runtime failure path.

            # SNAPSTART-001, SNAPSTART-002, SNAPSTART-008, SNAPSTART-009
            if (
                isinstance(runtime, str)
                and runtime in self._runtime_region_support
            ):
                supported_regions = self._runtime_region_support[runtime]
                unsupported_regions = [
                    region
                    for region in validator.context.regions
                    if region not in supported_regions
                ]
                if unsupported_regions:
                    yield ValidationError(
                        (
                            "'SnapStart' enabled functions are not supported in "
                            f"{unsupported_regions!r}"
                        ),
                        path=deque(["SnapStart", "ApplyOn"]),
                    )
                continue

            # SNAPSTART-004 logic obligation: preserve the negative-case matrix.
            # DECISION/FLOW:
            # 1. A capability-mapped runtime is handled above per selected region;
            #    any region outside its allowlist emits the regional E2530.
            # 2. Every unmapped runtime is handed to the legacy checks below without
            #    changing their region boundary or supported Java-runtime behavior.
            # 3. Emit the regional E2530 for each unsupported selected-region set,
            #    then emit the runtime E2530 when the resolved string is neither a
            #    supported Java runtime nor an exact capability-map match.
            # FAILURE/HANDOFF: unresolved non-string runtimes stop before string-only
            # checks; all existing diagnostic messages and paths remain unchanged.

            # SNAPSTART-003, SNAPSTART-004 architecture seam: this legacy branch
            # owns unmapped runtime and region rejection. The capability mapping
            # may depend on this fallback; this fallback must not depend on or infer
            # membership from capability-map keys.

            # SNAPSTART-005 logic obligation: preserve Java support independently.
            # INPUT: an enabled SnapStart configuration whose resolved runtime was
            # not consumed by the runtime-specific capability path above.
            # DECISION/FLOW:
            # 1. Determine regional validity exclusively against the existing Java
            #    support boundary in self.regions; do not consult, intersect, or
            #    substitute any _runtime_region_support allowlist.
            # 2. If any selected region is outside that Java boundary, hand the
            #    unsupported set to the existing regional E2530 failure path.
            # 3. Otherwise preserve acceptance for Java runtimes recognized by the
            #    legacy runtime check, including every previously valid Java case.
            # OUTPUT: a valid Java runtime/region combination yields no E2530 even
            # when Python 3.12 availability for the same region differs.
            # FAILURE/HANDOFF: only the Java boundary may reject a Java configuration;
            # non-Java and unresolved runtimes continue to their existing checks.

            # SNAPSTART-005 architecture seam: exact capability-map dispatch may
            # hand unmatched runtimes to this legacy boundary, but the dependency
            # ends at that handoff. The Java region and runtime contracts below do
            # not read from the runtime-specific capability mapping.

            if any(region not in self.regions for region in validator.context.regions):
                unsupported_regions = [
                    region
                    for region in validator.context.regions
                    if region not in self.regions
                ]
                yield ValidationError(
                    (
                        "'SnapStart' enabled functions are not supported in "
                        f"{unsupported_regions!r}"
                    ),
                    path=deque(["SnapStart", "ApplyOn"]),
                )

            # Validate runtime is a string before using startswith
            if not isinstance(runtime, str):
                continue

            if (
                runtime
                and (not runtime.startswith("java"))
                and runtime not in ["java8.al2", "java8"]
            ):
                yield ValidationError(
                    f"{runtime!r} is not supported for 'SnapStart' enabled functions",
                    path=deque(["SnapStart", "ApplyOn"]),
                )
