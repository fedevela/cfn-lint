"""
Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from __future__ import annotations

from typing import Any, List, Tuple

from cfnlint.match import Match

# Architecture boundary — GUID: CFNLINT-008
# Transform implementations own intrinsic resolution and report an unresolvable
# expression across this seam as (non-empty diagnostics, None). The transform
# coordinator owns template replacement and may commit only the complementary
# success shape (empty diagnostics, transformed template). Runner-level rule
# configuration may filter the diagnostics, but does not own or alter this outcome.
TransformResult = Tuple[List[Match], Any]
