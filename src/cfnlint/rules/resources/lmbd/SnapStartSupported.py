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

    # SNAPSTART-001, SNAPSTART-002, SNAPSTART-008: E2530 owns the private
    # runtime/region capability boundary. Implementations populate this contract
    # from AWS regional-availability data; callers must not supply capability data.
    _runtime_region_support: Mapping[str, AbstractSet[str]]

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
        self.regions = [
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

            # SNAPSTART-001, SNAPSTART-002, SNAPSTART-008, SNAPSTART-009:
            # IF runtime is "python3.12":
            #   SNAPSTART-009: SET selected_regions to validator.context.regions so
            #   explicit and implicit selection retain existing cfn-lint semantics.
            #   SET unsupported_regions to an empty collection.
            #   FOR EACH region in selected_regions:
            #     LOOK UP support for the Python 3.12 and SnapStart combination in
            #     that region's existing AWS regional-availability data.
            #     SNAPSTART-001: IF supported, emit no E2530 for that region.
            #     SNAPSTART-002, SNAPSTART-008: ELSE append the region to
            #     unsupported_regions, independently of every other region.
            #   SNAPSTART-002, SNAPSTART-008: IF unsupported_regions is not empty,
            #   emit an unsupported SnapStart E2530 identifying only those regions.
            #   END this scenario's runtime evaluation so supported Python 3.12 is
            #   not rejected by the generic non-Java runtime failure path below.

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
