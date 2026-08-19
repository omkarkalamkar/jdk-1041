"""ReleaseResources context dataclasses for CentralNode."""

import logging
from dataclasses import dataclass
from typing import Callable

from ska_tmc_common.v4.command_context import CommandRuntimeContext

from ska_tmc_centralnode.model.input import (
    InputParameterLow,
    InputParameterMid,
)

from ..assignresources.common_context import (
    CommandInProgressContext,
    ObsStateContext,
)
from .release_resources_strategy import (
    LowReleaseResourcesStrategy,
    MidReleaseResourcesStrategy,
)


@dataclass(kw_only=True)
class ReleaseResourcesContext(CommandRuntimeContext):
    """Runtime context required for ReleaseResources execution.

    Inherits CommandRuntimeContext so that command_completion_condition
    and command_timeout are available to BaseTMCCommand — same fix
    applied to AssignResourcesContext.
    """

    update_abort_evt: Callable
    input_parameter: InputParameterMid | InputParameterLow
    obs_state_ctx: ObsStateContext
    cmd_inprogress_ctx: CommandInProgressContext
    subarray_trl_prefix: str


@dataclass(kw_only=True)
class MidReleaseResourcesContext(ReleaseResourcesContext):
    """MID-specific ReleaseResources runtime context."""

    def make_strategy(
        self, logger: logging.Logger
    ) -> MidReleaseResourcesStrategy:
        """Create MID ReleaseResources strategy."""
        return MidReleaseResourcesStrategy(logger)


@dataclass(kw_only=True)
class LowReleaseResourcesContext(ReleaseResourcesContext):
    """LOW-specific ReleaseResources runtime context."""

    is_auto_recovery_enabled: bool
    pop_subsystem_assigned_per_subarray_id: Callable

    def make_strategy(
        self, logger: logging.Logger
    ) -> LowReleaseResourcesStrategy:
        """Create LOW ReleaseResources strategy."""
        return LowReleaseResourcesStrategy(logger)
