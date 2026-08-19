"""
Contains the runtime context classes for the SetGlobalPointingModel command.
"""

import json
import logging
from dataclasses import dataclass
from json import JSONDecodeError
from threading import RLock, Event
from typing import Callable
from ska_tmc_common import DeviceInfo
from ska_tmc_common.v4.command_context import CommandRuntimeContext

from ska_tmc_centralnode.refactored_commands.set_gpm.strategy import (
    GPMStrategy,
)

from ska_tmc_centralnode.manager.event_data_manager import EventDataManager
@dataclass(kw_only=True)
class GPMContext(CommandRuntimeContext):
    """Runtime context containing parameters for GPM command execution.

    command_timeout: Timeout for the GPM command.
    get_id: Callback to get the command ID.
    update_id: Callback to update the command ID.
    update_name: Callback to update the command name.
    clear: Callback to clear command data.
    get_name: Callback to get the command name.
    gpm_unknown_dishes: List of dishes with unknown GPM data.
    dishln_gpm_cmd_exe_data: GPM command execution data by dish.
    is_already_assigned: Callback to check dish assignment.
    update_abort_evt: Callback to update the abort event.
    get_dish_leaf_node_device_names: Callback to get dish device names.
    default_gpm_version_params: Default GPM version parameters.
    get_device: Callback to retrieve a device.
    dish_leaf_node_prefix: Prefix used for dish leaf node devices.
    get_evt_data_manager: Callback to get the event data manager.
    dishln_gpm_lock: Lock protecting dish GPM data.
    global_pointing_model_status: GPM status for each dish.
    reset_gpm_data: Callback to reset GPM command data.
    """

    command_timeout: float
    update_name: Callable[[str],None]
    clear: Callable[[],None]
    get_name: Callable[[],str]
    gpm_unknown_dishes: list[str]
    dishln_gpm_cmd_exe_data: dict
    is_already_assigned: Callable[[str],bool]
    update_abort_evt: Callable[[Event], None]
    get_dish_leaf_node_device_names: Callable[[],list]
    default_gpm_version_params: dict
    get_device: Callable[[str],DeviceInfo]
    dish_leaf_node_prefix: str
    get_evt_data_manager: Callable[[],EventDataManager]
    dishln_gpm_lock: RLock
    global_pointing_model_status: dict
    reset_gpm_data: Callable[[], None]

    def make_strategy(self, logger: logging.Logger) -> "GPMStrategy":
        """Create a global pointing model strategy.

        Args:
            logger: Logger instance for strategy operations.

        Returns:
            GPMStrategy: Global pointing model strategy.
        """

        return GPMStrategy(
            logger,
            self.gpm_unknown_dishes,
            self.default_gpm_version_params,
        )


class GPMRequestError(ValueError):
    """Raised when JSON parsing of GPM request fails."""


class GPMRequest:
    """Parsed global pointing model request from JSON input."""

    def __init__(self, data: dict) -> None:
        self.data = data

    @classmethod
    def from_json(cls, argin: str) -> "GPMRequest":
        """Parse JSON input into a Global pointing model request."""
        try:
            return json.loads(argin)
        except JSONDecodeError as json_error:
            raise GPMRequestError(
                f"JSON parsing failed with exception: {json_error}"
            ) from json_error
