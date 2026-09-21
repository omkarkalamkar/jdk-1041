"""Data classes used by CentralNode TelescopeOn refactor."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(slots=True)
class TelescopeOnPlan:
    """Execution plan produced by TelescopeOnStrategy.

    TelescopeOn has no JSON payload, so the plan mainly carries the ordered
    list of target device names (and any Mid-specific dish filtering result).
    """

    # Ordered list of device names that should receive the "On" command
    on_targets: List[str] = field(default_factory=list)

    # Mid only: dishes that need SetStandbyFPMode
    standby_fp_targets: List[str] = field(default_factory=list)

    # Devices that were unavailable at plan-build time
    unavailable_devices: List[str] = field(default_factory=list)
