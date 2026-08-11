"""ReleaseResources context dataclasses for CentralNode."""

import logging
from dataclasses import dataclass
from typing import Callable

from ska_tmc_centralnode.model.input import (
    InputParameterLow,
    InputParameterMid,
)

from .release_resources_plan import (
    LowReleaseResourcesPlan,
    MidReleaseResourcesPlan,
)
from .release_resources_strategy import (
    LowReleaseResourcesStrategy,
    MidReleaseResourcesStrategy,
)


@dataclass
class SubarrayIDContext:
    """Context to maintain subarray ID state."""

    set: Callable
    get: Callable
    reset: Callable


@dataclass(kw_only=True)
class ReleaseResourcesContext:
    """Runtime context required for ReleaseResources execution."""

    subarray_id_ctx: SubarrayIDContext
    input_parameter: InputParameterMid | InputParameterLow

    def make_strategy(self, logger: logging.Logger):
        """Create a telescope-specific ReleaseResources strategy."""
        raise NotImplementedError


@dataclass(kw_only=True)
class MidReleaseResourcesContext(ReleaseResourcesContext):
    """MID-specific ReleaseResources runtime context."""

    def make_strategy(
        self, logger: logging.Logger
    ) -> MidReleaseResourcesStrategy:
        """Create MID ReleaseResources strategy."""
        return MidReleaseResourcesStrategy(logger)

    def apply_plan(self, plan: MidReleaseResourcesPlan) -> None:
        """Apply MID plan values into context callbacks."""
        self.subarray_id_ctx.set(plan.subarray_id)


@dataclass(kw_only=True)
class LowReleaseResourcesContext(ReleaseResourcesContext):
    """LOW-specific ReleaseResources runtime context."""

    mccs_release_interface: str

    def make_strategy(
        self, logger: logging.Logger
    ) -> LowReleaseResourcesStrategy:
        """Create LOW ReleaseResources strategy."""
        return LowReleaseResourcesStrategy(logger, self.mccs_release_interface)

    def apply_plan(self, plan: LowReleaseResourcesPlan) -> None:
        """Apply LOW plan values into context callbacks."""
        self.subarray_id_ctx.set(plan.subarray_id)
