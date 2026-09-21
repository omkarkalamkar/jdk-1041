"""TelescopeOn context dataclasses for CentralNode."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from threading import Event
from typing import Any, Callable, Dict, List, Optional

from ska_tmc_common import DeviceInfo
from ska_tmc_common.v4.command_context import CommandRuntimeContext
from tango import DevState

from ..common.common_context import CommandInProgressContext
from .telescope_on_strategy import (
    LowTelescopeOnStrategy,
    MidTelescopeOnStrategy,
    TelescopeOnStrategy,
)


@dataclass(kw_only=True)
class TelescopeOnContext(CommandRuntimeContext):
    """Runtime context required for TelescopeOn execution (shared Mid/Low)."""

    # Command tracking
    cmd_inprogress_ctx: CommandInProgressContext
    update_abort_evt: Callable[[Event], None]
    log_state: Callable[[str], None]

    # Component / desired state
    component: Any  # CentralComponent (or equivalent)

    @property
    def desired_telescope_state(self) -> DevState:
        """Return the desired telescope state stored on the component."""
        return self.component.desired_telescope_state

    @desired_telescope_state.setter
    def desired_telescope_state(self, value: DevState) -> None:
        """Set the desired telescope state on the component."""
        self.component.desired_telescope_state = value

    # Device name helpers
    csp_mln_dev_name: str
    sdp_mln_dev_name: str
    subarray_trl_prefix: str

    # Availability checks (bound methods from component manager)
    check_if_csp_mln_is_available: Callable[[], bool]
    check_if_sdp_mln_is_available: Callable[[], bool]

    # Device discovery helpers
    get_subarray_device_names: Callable[[], List[str]]
    get_device: Callable[[str], Optional[DeviceInfo]]

    def make_strategy(self, logger: logging.Logger) -> TelescopeOnStrategy:
        """Create a telescope-specific strategy. Overridden in Mid/Low."""
        raise NotImplementedError


@dataclass(kw_only=True)
class MidTelescopeOnContext(TelescopeOnContext):
    """MID-specific TelescopeOn runtime context."""

    # name -> DeviceInfo-like object that exposes .dishMode
    get_dish_devices: Callable[[], Dict[str, Any]]

    def make_strategy(self, logger: logging.Logger) -> MidTelescopeOnStrategy:
        """Create MID TelescopeOn strategy."""
        return MidTelescopeOnStrategy(logger)


@dataclass(kw_only=True)
class LowTelescopeOnContext(TelescopeOnContext):
    """LOW-specific TelescopeOn runtime context."""

    mccs_mln_dev_name: str
    check_if_mccs_mln_is_available: Callable[[], bool]

    def make_strategy(self, logger: logging.Logger) -> LowTelescopeOnStrategy:
        """Create LOW TelescopeOn strategy."""
        return LowTelescopeOnStrategy(logger)
