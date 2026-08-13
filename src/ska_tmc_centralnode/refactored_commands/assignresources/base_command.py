"""Base command module.

This module provides common event-callback and adapter-resolution
helpers for refactored CentralNode commands, mirroring BaseSNCommand's
role for SubarrayNode commands.
"""

import json
import logging
from datetime import datetime
from typing import Optional

from ska_control_model import ObsState, ResultCode
from ska_tmc_common.adapters import AdapterFactory, AdapterType
from ska_tmc_common.v4.command_context import (
    CommandRuntimeContext,
    DeviceCommand,
)
from ska_tmc_common.v4.tmc_command import BaseTMCCommand

from ska_tmc_centralnode.model.input import InputParameterMid

LOGGER = logging.getLogger(__name__)
ADAPTER_INIT_ERROR = "Exception in creating adapter for %s, Exception: %s"


class BaseCNCommand(BaseTMCCommand):
    """Base class for refactored CentralNode commands."""

    # pylint:disable=keyword-arg-before-vararg
    def __init__(
        self,
        component_manager,
        adapter_factory=None,
        *args,
        logger=LOGGER,
        **kwargs,
    ):
        self.component_manager = component_manager
        self._adapter_factory = adapter_factory or AdapterFactory()

        super().__init__(
            self._build_command_runtime_context(),
            self._adapter_factory,
            logger or LOGGER,
        )

        self.mccs_mln_adapter = None
        self.tm_subarray_adapter = None
        self.subarray_devname = ""
        self.dish_adapters = []
        self.subarray_adapters = []
        self.subarray_id: int | str = 0

    def _build_command_runtime_context(self) -> CommandRuntimeContext:
        """Build (or fetch) the runtime context for this command.

        Subclasses must override this to call the appropriate
        component-manager context builder
        (e.g. ``_get_assign_context`` / ``_get_release_context``).

        :raises NotImplementedError: if not overridden by a subclass.
        """
        raise NotImplementedError(
            "Subclasses of BaseCNCommand must implement "
            "_build_command_runtime_context()"
        )

    def _update_event_callback(
        self, device_name: str, command_id: str, result: str
    ) -> None:
        """Update the event data for the following device.

        :param device_name: Device name
        :type device_name: str
        :param command_id: command id
        :type command_id: str
        :param result: result code and message in string.
        :type result: str
        """
        if result:
            self.logger.debug(
                "Got Command Result for %s %s", device_name, result
            )
            self._update_event_data_storage(device_name, command_id, result)

    def _update_event_data_storage(
        self,
        device_name: str,
        command_id: str,
        result: str,
        timestamp: Optional[datetime] = None,
        data_type: str = "CommandResultData",
    ) -> None:
        """Method to update event data storage.

        :param device_name: device name.
        :type device_name: str
        :param command_id: command id.
        :type command_id: str
        :param result: result data as string with resultcode and message.
        :type result: str
        :param timestamp: timestamp, defaults to now if not provided.
        :type timestamp: Optional[datetime]
        :param data_type: datatype of event data storage, defaults to
            "CommandResultData"
        :type data_type: str, optional
        """
        if timestamp is None:
            timestamp = datetime.now()

        if self.command_runtime_context is None:
            return

        event_manager = self.command_runtime_context.get_evt_data_manager()
        event_manager.update_event_data(
            device=device_name,
            data=(command_id, result),
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
        if self.command_runtime_context is None:
            return

        self.command_runtime_context.get_evt_data_manager().update_event_data(
            device=cmd_ctx.device_name,
            data=(
                self.context.command_device_ids[cmd_ctx.device_name],
                json.dumps([ResultCode.UNKNOWN, ""]),
            ),
            received_timestamp=None,
            data_type="CommandResultData",
        )

    def _set_subarray_obs_state_to_fault_on_command_timeout(self) -> None:
        """Method to set Subarray Node ObsState to FAULT when timeout
        occurs on the subarray or one of the leaf nodes."""
        self.command_runtime_context.obs_state_ctx.change_callback(
            {"component_obsfault": None}
        )

    def init_adapters(self) -> None:
        """Initialise adapters for MID or LOW command execution."""
        if isinstance(
            self.component_manager.input_parameter, InputParameterMid
        ):
            self.init_adapters_mid()
        else:
            self.init_adapters_low()

    def get_subarray_adapter(self, subarray_id: int) -> None:
        """Resolve and store the adapter for the target subarray.

        :raises ValueError: if the subarray does not exist or has no
            responsive adapter.
        """
        subarray_adapter_dev_name = (
            self.component_manager.subarray_trl_prefix
            + str(subarray_id).zfill(2)
        )
        self.logger.debug(
            "Command ID: %s | Attempting to get adapter for Subarray: %s",
            self.context.command_id,
            subarray_adapter_dev_name,
        )

        for adapter in self.subarray_adapters:
            if adapter.dev_name == subarray_adapter_dev_name:
                self.tm_subarray_adapter = adapter
                self.subarray_devname = adapter.dev_name
                return

        raise ValueError(
            f"Subarray Id {subarray_id}({subarray_adapter_dev_name}) is"
            " not existing!"
        )

    def prepare_subarray_command_target(self) -> None:
        """Initialise adapters and resolve the target subarray adapter."""
        self.init_adapters()
        self.get_subarray_adapter(int(self.subarray_id))

    def get_subarray_obsstate(self) -> ObsState:
        """Return current obsState of the target subarray."""
        return self.component_manager.get_subarray_obsstate(
            self.subarray_devname
        )

    def init_adapters_mid(self) -> None:
        """Initialise MID adapters required for command execution.

        :raises ValueError: if no working subarray or dish adapters
            could be created.
        """
        self.dish_adapters = []
        self.subarray_adapters = []
        error_dev_names = []
        num_working = 0

        for (
            dev_name
        ) in self.component_manager.input_parameter.subarray_dev_names:
            dev_info = self.component_manager.get_device(dev_name)
            if not dev_info.unresponsive:
                try:
                    self.subarray_adapters.append(
                        self._adapter_factory.get_or_create_adapter(
                            dev_name, AdapterType.SUBARRAY
                        )
                    )
                    num_working += 1
                    self.logger.debug(
                        "Adapter is created for subarray: %s ", dev_name
                    )
                except Exception as exception:
                    self.logger.exception(
                        ADAPTER_INIT_ERROR, dev_name, str(exception)
                    )
                    error_dev_names.append(dev_name)

        if num_working == 0:
            faulty_dev = ".".join(error_dev_names)
            raise ValueError(
                f"Error in creating tm subarray adapters {faulty_dev},"
            )

        error_dev_names = []
        num_working = 0
        for (
            dev_name
        ) in self.component_manager.input_parameter.dish_leaf_node_dev_names:
            dev_info = self.component_manager.get_device(dev_name)
            if not dev_info.unresponsive:
                try:
                    self.dish_adapters.append(
                        self._adapter_factory.get_or_create_adapter(
                            dev_name, AdapterType.DISH
                        )
                    )
                    num_working += 1
                    self.logger.debug(
                        "Adapter is created for DishLeafNode: %s", dev_name
                    )
                except Exception as exception:
                    self.logger.exception(
                        ADAPTER_INIT_ERROR, dev_name, str(exception)
                    )
                    error_dev_names.append(dev_name)

        if num_working == 0:
            raise ValueError(
                f"Error in creating dish adapters {'.'.join(error_dev_names)}"
            )

    def init_adapters_low(self) -> None:
        """Initialise LOW adapters required for command execution.

        :raises ValueError: if adapters could not be created.
        """
        self.mccs_mln_adapter = None
        self.subarray_adapters = []

        self.mccs_mln_adapter = self._adapter_factory.get_or_create_adapter(
            self.component_manager.input_parameter.mccs_mln_dev_name,
            AdapterType.MCCS_MASTER_LEAF_NODE,
        )

        error_dev_names = []
        num_working = 0

        for (
            dev_name
        ) in self.component_manager.input_parameter.subarray_dev_names:
            dev_info = self.component_manager.get_device(dev_name)
            if not dev_info.unresponsive:
                try:
                    self.subarray_adapters.append(
                        self._adapter_factory.get_or_create_adapter(
                            dev_name, AdapterType.SUBARRAY
                        )
                    )
                    num_working += 1
                except Exception as exception:
                    self.logger.exception(
                        ADAPTER_INIT_ERROR, dev_name, str(exception)
                    )
                    error_dev_names.append(dev_name)

        if num_working == 0:
            faulty_dev = ".".join(error_dev_names)
            raise ValueError(
                f"Error in creating tm subarray adapters {faulty_dev},"
            )
