"""Data classes used by CentralNode TelescopeOff refactor."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(slots=True)
class TelescopeOffPlan:
    """Execution plan produced by TelescopeOffStrategy.

    TelescopeOff has no JSON payload, so the plan mainly carries the ordered
    list of target device names, split into two phases:

    Phase 1: Turn off subarrays, then wait for EMPTY obsState.
    Phase 2: Turn off remaining devices (dishes/MCCS, CSP, SDP).
    """

    # Phase 1: Subarray device names that should receive the "Off" command
    subarray_off_targets: List[str] = field(default_factory=list)

    # Phase 2: Ordered list of non-subarray devices for "Off" command
    # (CSP MLN, SDP MLN, and for Low: MCCS MLN)
    off_targets: List[str] = field(default_factory=list)

    # Mid only: dishes that need the "Off" command
    dish_off_targets: List[str] = field(default_factory=list)

    # Devices that were unavailable at plan-build time
    unavailable_devices: List[str] = field(default_factory=list)
