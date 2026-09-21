"""
Contains the runtime context classes for the SetStowMode command.
"""

from dataclasses import dataclass
from threading import Event
from typing import Callable

from ska_tmc_common import DishMode
from ska_tmc_common.v4.command_context import CommandRuntimeContext

from ..common.common_context import CommandInProgressContext


@dataclass(kw_only=True)
class StowContext(CommandRuntimeContext):
    """Runtime context containing parameters for GPM command execution.
    cmd_inprogress_ctx: CommandInProgressContext
    update_abort_evt: Callback to update the abort event.
    get_dish_leaf_node_device_names: Callback to get dish device names.
    dish_leaf_node_prefix: Prefix used for dish leaf node devices.
    """

    cmd_inprogress_ctx: CommandInProgressContext
    update_abort_evt: Callable[[Event], None]
    dish_leaf_node_prefix: str
    get_current_dish_mode_of_dln: Callable[[str], DishMode]

    def update_cmd_name(self, command_name: str):
        """Method to update command name."""
        self.cmd_inprogress_ctx.update_name(command_name)

    def get_cmd_name(self) -> str:
        """Method to get command name."""
        return self.cmd_inprogress_ctx.get_name()

    def clear_cmd_name(self) -> str:
        """Method to clear command name."""
        return self.cmd_inprogress_ctx.clear()
