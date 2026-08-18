"""
Contains the runtime context classes for the SetGlobalPointingModel command.
"""

import json
import logging
from dataclasses import dataclass
from json import JSONDecodeError
from threading import Lock
from typing import Callable

from ska_tmc_common.v4.command_context import CommandRuntimeContext

from ska_tmc_centralnode.refactored_commands.set_gpm.strategy import (
    GPMStrategy,
)


@dataclass
class CommandInProgressContext:
    """Context to maintain command in progress data.

    Attributes:
        get_id: Callable to fetch current command in progress id.
        update_id: Callable to update current command in progress id.
        update_name: Callable to update current command in progress name.
        clear: Callable to clear the command object from
        in progress object list.
        get_name: Callable to get command in progress.
        obj_update_cmd: Callable to update command in progress
        object with current command.
    """

    get_id: Callable
    update_id: Callable
    update_name: Callable
    clear: Callable
    get_name: Callable
    obj_update_cmd: Callable


@dataclass(kw_only=True)
class GPMContext(CommandRuntimeContext):
    """GPM context containing runtime parameters for the Mid telescope
    Subarray."""

    command_timeout: float
    cmd_inprogress_ctx: CommandInProgressContext
    gpm_unknown_dishes: list
    dishln_gpm_cmd_exe_data: dict
    is_already_assigned: Callable
    update_abort_evt: Callable
    get_dish_leaf_node_device_names: Callable
    default_gpm_version_params: dict
    get_device: Callable
    dish_leaf_node_prefix: str
    get_evt_data_manager: Callable
    dishln_gpm_lock: Lock
    global_pointing_model_status: dict
    reset_gpm_data: Callable

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
