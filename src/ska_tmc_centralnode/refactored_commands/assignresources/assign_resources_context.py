"""AssignResources context dataclasses for CentralNode."""

import logging
from dataclasses import dataclass
from typing import Callable

from ska_tmc_common.v4.command_context import CommandRuntimeContext

from ska_tmc_centralnode.model.input import (
    InputParameterLow,
    InputParameterMid,
)

from ..common.common_context import CommandInProgressContext, ObsStateContext
from .assign_resources_strategy import (
    LowAssignResourcesStrategy,
    MidAssignResourcesStrategy,
)


@dataclass
class ArrayLayoutContext:
    """Context to maintain array layout behavior."""

    update_url: Callable
    get_default_url: Callable


@dataclass(kw_only=True)
class AssignResourcesContext(CommandRuntimeContext):
    """Runtime context required for AssignResources execution."""

    cmd_inprogress_ctx: CommandInProgressContext
    array_layout_ctx: ArrayLayoutContext
    obs_state_ctx: ObsStateContext
    input_parameter: InputParameterMid | InputParameterLow
    update_abort_evt: Callable
    log_state: Callable
    subarray_trl_prefix: str

    def make_strategy(self, logger: logging.Logger):
        """Create a telescope-specific AssignResources strategy."""
        raise NotImplementedError


@dataclass(kw_only=True)
class MidAssignResourcesContext(AssignResourcesContext):
    """MID-specific AssignResources runtime context."""

    is_already_assigned: Callable

    def make_strategy(
        self, logger: logging.Logger
    ) -> MidAssignResourcesStrategy:
        """Create MID AssignResources strategy."""
        return MidAssignResourcesStrategy(logger)


@dataclass(kw_only=True)
class LowAssignResourcesContext(AssignResourcesContext):
    """LOW-specific AssignResources runtime context."""

    get_assigned_subsystems: Callable
    set_assigned_subsystems: Callable
    is_auto_recovery_enabled: bool
    mccs_mln_dev_name: str

    def make_strategy(
        self, logger: logging.Logger
    ) -> LowAssignResourcesStrategy:
        """Create LOW AssignResources strategy."""
        return LowAssignResourcesStrategy(logger)

    def apply_plan(self, plan):
        """Apply the plan to the context."""
        self.set_assigned_subsystems(plan.subarray_id, plan.subsystems)
