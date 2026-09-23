"""TelescopeOff strategy implementations for CentralNode."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from .telescope_off_plan import TelescopeOffPlan

if TYPE_CHECKING:
    from .telescope_off_context import (
        LowTelescopeOffContext,
        MidTelescopeOffContext,
        TelescopeOffContext,
    )


class TelescopeOffStrategy(ABC):
    """Abstract base class for telescope-specific TelescopeOff behaviour."""

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    @abstractmethod
    def build_plan(self, context: "TelescopeOffContext") -> TelescopeOffPlan:
        """Build the execution plan from the runtime context."""


class MidTelescopeOffStrategy(TelescopeOffStrategy):
    """TelescopeOff strategy for SKA Mid deployment.

    Execution order:
    Phase 1: Subarrays Off → wait for EMPTY obsState
    Phase 2: Dishes Off → CSP Off → SDP Off
    """

    def build_plan(
        self, context: "MidTelescopeOffContext"
    ) -> TelescopeOffPlan:
        plan = TelescopeOffPlan()

        # Phase 1: All subarrays
        plan.subarray_off_targets.extend(context.get_subarray_device_names())

        # Phase 2a: All dishes
        dish_devices = context.get_dish_devices()
        for dev_name in dish_devices:
            plan.dish_off_targets.append(dev_name)

        # Phase 2b: CSP Master Leaf Node
        if context.check_if_csp_mln_is_available():
            plan.off_targets.append(context.csp_mln_dev_name)
        else:
            plan.unavailable_devices.append(context.csp_mln_dev_name)

        # Phase 2c: SDP Master Leaf Node
        if context.check_if_sdp_mln_is_available():
            plan.off_targets.append(context.sdp_mln_dev_name)
        else:
            plan.unavailable_devices.append(context.sdp_mln_dev_name)

        self.logger.debug(
            "Mid TelescopeOff plan: subarrays=%s, dishes=%s, "
            "off=%s, unavailable=%s",
            plan.subarray_off_targets,
            plan.dish_off_targets,
            plan.off_targets,
            plan.unavailable_devices,
        )
        return plan


class LowTelescopeOffStrategy(TelescopeOffStrategy):
    """TelescopeOff strategy for SKA Low deployment.

    Execution order:
    Phase 1: Subarrays Off → wait for EMPTY obsState
    Phase 2: MCCS Off → CSP Off → SDP Off
    """

    def build_plan(
        self, context: "LowTelescopeOffContext"
    ) -> TelescopeOffPlan:
        plan = TelescopeOffPlan()

        # Phase 1: All subarrays
        plan.subarray_off_targets.extend(context.get_subarray_device_names())

        # Phase 2a: MCCS Master Leaf Node
        if context.check_if_mccs_mln_is_available():
            plan.off_targets.append(context.mccs_mln_dev_name)
        else:
            plan.unavailable_devices.append(context.mccs_mln_dev_name)

        # Phase 2b: CSP Master Leaf Node
        if context.check_if_csp_mln_is_available():
            plan.off_targets.append(context.csp_mln_dev_name)
        else:
            plan.unavailable_devices.append(context.csp_mln_dev_name)

        # Phase 2c: SDP Master Leaf Node
        if context.check_if_sdp_mln_is_available():
            plan.off_targets.append(context.sdp_mln_dev_name)
        else:
            plan.unavailable_devices.append(context.sdp_mln_dev_name)

        self.logger.debug(
            "Low TelescopeOff plan: subarrays=%s, off=%s, unavailable=%s",
            plan.subarray_off_targets,
            plan.off_targets,
            plan.unavailable_devices,
        )
        return plan
