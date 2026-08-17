"""Base command module.

This module provides functions to execute the Subarray Node commands.
"""

# pylint: enable=invalid-name, protected-access, unused-argument
# pylint: enable=arguments-differ, signature-differs, too-many-function-args
import json
from datetime import datetime

from ska_control_model import ResultCode
from ska_tmc_common.v4.command_context import DeviceCommand
from ska_tmc_common.v4.tmc_command import BaseTMCCommand


class BaseCNCommand(BaseTMCCommand):
    """A class to execute the BaseCNCommand."""

    def _update_event_callback(
        self, device_name: str, command_id: str, result: str
    ) -> None:
        """Update the event data for the following device.

        :param device_name: Device name
        :type device_name: str
        :param command_id: command id
        :type command_id: str
        :param result: result code and message in string.
        :type result: tuple
        """
        if result:
            self.logger.debug(
                "Got Command Result for %s %s", device_name, result
            )
            self._update_event_data_strorage(device_name, command_id, result)

    def _update_event_data_strorage(
        self,
        device_name: str,
        command_id: str,
        result: str,
        timestamp: datetime = datetime.now(),
        data_type="CommandResultData",
    ) -> None:
        """Method to update event data storage.

        :param device_name: device name.
        :type device_name: str
        :param result: result data as string with resultcode and
            message.
        :type result: str
        :param timestamp: timestamp, defaults to datetime.now()
        :type timestamp: datetime, optional
        :param data_type: datatupe of event data storage, defaults to
            "CommandResultData"
        :type data_type: str, optional
        """

        if timestamp is None:
            timestamp = datetime.now()

        if self.command_runtime_context is None:
            return

        ev_mgr = self.command_runtime_context.get_evt_data_manager()
        ev_mgr.update_event_data(
            device=device_name,
            data=(
                command_id,
                result,
            ),
            received_timestamp=timestamp,
            data_type=data_type,
        )
        cond = self.context.completion_condition
        with cond:
            cond.notify_all()

    def command_invoked_callback(self, cmd_ctx: DeviceCommand) -> None:
        """The callback to process the command details after invocation.

        :param cmd_ctx: The device command object with details related
            to current invoked command.
        :type cmd_ctx: DeviceCommand
        """
        self.command_runtime_context.get_evt_data_manager().update_event_data(
            device=cmd_ctx.device_name,
            data=(
                self.context.command_device_ids[cmd_ctx.device_name],
                json.dumps([ResultCode.UNKNOWN, ""]),
            ),
            received_timestamp=None,
            data_type="CommandResultData",
        )
