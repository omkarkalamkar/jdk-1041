"""TelescopeOn strategy implementations for CentralNode."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from ska_tmc_common.enum import DishMode

from .telescope_on_plan import TelescopeOnPlan

if TYPE_CHECKING:
    from .telescope_on_context import (
        LowTelescopeOnContext,
        MidTelescopeOnContext,
        TelescopeOnContext,
    )


class TelescopeOnStrategy(ABC):
    """Abstract base class for telescope-specific TelescopeOn behaviour."""

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    @abstractmethod
    def build_plan(self, context: "TelescopeOnContext") -> TelescopeOnPlan:
        """Build the execution plan from the runtime context."""


class MidTelescopeOnStrategy(TelescopeOnStrategy):
    """TelescopeOn strategy for SKA Mid deployment."""

    def build_plan(self, context: "MidTelescopeOnContext") -> TelescopeOnPlan:
        plan = TelescopeOnPlan()

        # 1. Dishes that are not already in STANDBY_FP
        dish_devices = context.get_dish_devices()
        for dev_name, dish_info in dish_devices.items():
            if getattr(dish_info, "dishMode", None) != DishMode.STANDBY_FP:
                plan.standby_fp_targets.append(dev_name)

        # 2. CSP Master Leaf Node
        if context.check_if_csp_mln_is_available():
            plan.on_targets.append(context.csp_mln_dev_name)
        else:
            plan.unavailable_devices.append(context.csp_mln_dev_name)

        # 3. SDP Master Leaf Node
        if context.check_if_sdp_mln_is_available():
            plan.on_targets.append(context.sdp_mln_dev_name)
        else:
            plan.unavailable_devices.append(context.sdp_mln_dev_name)

        # 4. Subarrays
        plan.on_targets.extend(context.get_subarray_device_names())

        self.logger.debug(
            "Mid TelescopeOn plan: standby_fp=%s, on=%s, unavailable=%s",
            plan.standby_fp_targets,
            plan.on_targets,
            plan.unavailable_devices,
        )
        return plan


class LowTelescopeOnStrategy(TelescopeOnStrategy):
    """TelescopeOn strategy for SKA Low deployment."""

    def build_plan(self, context: "LowTelescopeOnContext") -> TelescopeOnPlan:
        plan = TelescopeOnPlan()

        # 1. MCCS Master Leaf Node
        if context.check_if_mccs_mln_is_available():
            plan.on_targets.append(context.mccs_mln_dev_name)
        else:
            plan.unavailable_devices.append(context.mccs_mln_dev_name)

        # 2. Subarrays
        plan.on_targets.extend(context.get_subarray_device_names())

        # 3. CSP Master Leaf Node
        if context.check_if_csp_mln_is_available():
            plan.on_targets.append(context.csp_mln_dev_name)
        else:
            plan.unavailable_devices.append(context.csp_mln_dev_name)

        # 4. SDP Master Leaf Node
        if context.check_if_sdp_mln_is_available():
            plan.on_targets.append(context.sdp_mln_dev_name)
        else:
            plan.unavailable_devices.append(context.sdp_mln_dev_name)

        self.logger.debug(
            "Low TelescopeOn plan: on=%s, unavailable=%s",
            plan.on_targets,
            plan.unavailable_devices,
        )
        return plan
