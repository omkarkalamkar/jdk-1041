"""AssignResources context dataclasses for CentralNode."""

import logging
from dataclasses import dataclass
from typing import Callable

from ska_tmc_common.v4.command_context import CommandRuntimeContext

from ska_tmc_centralnode.model.input import (
    InputParameterLow,
    InputParameterMid,
)

from .assign_resources_plan import (
    LowAssignResourcesPlan,
    MidAssignResourcesPlan,
)
from .assign_resources_strategy import (
    LowAssignResourcesStrategy,
    MidAssignResourcesStrategy,
)
from .common_context import (
    AssignedResourcesAttributeContext,
    CommandInProgressContext,
    ObsStateContext,
    RecoveryContext,
    SbIDContext,
)


@dataclass
class ArrayLayoutContext:
    """Context to maintain array layout behavior."""

    download: Callable
    validate_schema: Callable
    update_url: Callable
    set: Callable


@dataclass
class SubarrayIDContext:
    """Context to maintain subarray ID state."""

    set: Callable
    get: Callable
    reset: Callable


@dataclass(kw_only=True)
class AssignResourcesContext(CommandRuntimeContext):
    """Runtime context required for AssignResources execution.

    Inherits CommandRuntimeContext so that command_completion_condition
    and command_timeout are available to BaseTMCCommand's
    initialize()/create_completion_context(), which read them directly
    off command_runtime_context.
    """

    cmd_inprogress_ctx: CommandInProgressContext
    array_layout_ctx: ArrayLayoutContext
    subarray_id_ctx: SubarrayIDContext
    sb_id_ctx: SbIDContext
    obs_state_ctx: ObsStateContext
    csp_assign_interface: str
    get_evt_data_manager: Callable
    input_parameter: InputParameterMid | InputParameterLow
    update_abort_evt: Callable
    get_dev_info: Callable

    def make_strategy(self, logger: logging.Logger):
        """Create a telescope-specific AssignResources strategy."""
        raise NotImplementedError


@dataclass
class DishLeafNodeContext:
    """Context for dish leaf node related operations."""

    set_device_names: Callable
    unsubscribe_events: Callable
    get_fqdn: Callable


@dataclass
class DishContext:
    """Context for dish related operations."""

    set_device_names: Callable


@dataclass(kw_only=True)
class MidAssignResourcesContext(AssignResourcesContext):
    """MID-specific AssignResources runtime context."""

    dishln_ctx: DishLeafNodeContext
    dish_ctx: DishContext
    assigned_resources_attr_ctx: AssignedResourcesAttributeContext
    set_sdpqc_fqdn: Callable
    remove_device_lp: Callable
    remove_dish: Callable

    def make_strategy(
        self, logger: logging.Logger
    ) -> MidAssignResourcesStrategy:
        """Create MID AssignResources strategy."""
        return MidAssignResourcesStrategy(
            logger, csp_interface=self.csp_assign_interface
        )

    def apply_plan(self, plan: MidAssignResourcesPlan) -> None:
        """Apply MID plan values into context callbacks."""
        self.subarray_id_ctx.set(plan.subarray_id)
        self.sb_id_ctx.set(plan.sb_id)
        self.set_sdpqc_fqdn([plan.scan_type_id, plan.visibilities_beam_id])


@dataclass
class AssignedSubsystemContext:
    """Context to maintain assigned subsystems."""

    update: Callable
    get: Callable
    set_configured: Callable


@dataclass(kw_only=True)
class LowAssignResourcesContext(AssignResourcesContext):
    """LOW-specific AssignResources runtime context."""

    recovery_ctx: RecoveryContext
    assigned_subsystem_ctx: AssignedSubsystemContext
    set_subarray_empty: Callable
    set_cmd_fail_info: Callable
    clear_cmd_fail_info: Callable
    set_subarr_to_be_cfgd: Callable

    def make_strategy(
        self, logger: logging.Logger
    ) -> LowAssignResourcesStrategy:
        """Create LOW AssignResources strategy."""
        return LowAssignResourcesStrategy(
            logger, csp_interface=self.csp_assign_interface
        )

    def apply_plan(self, plan: LowAssignResourcesPlan) -> None:
        """Apply LOW plan values into context callbacks."""
        self.subarray_id_ctx.set(plan.subarray_id)
        self.sb_id_ctx.set(plan.sb_id)
        self.assigned_subsystem_ctx.update(plan.subsystems)
        self.assigned_subsystem_ctx.set_configured(plan.subsystems)
