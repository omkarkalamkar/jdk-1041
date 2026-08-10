"""Base command module.

This module provides common command callbacks and execution helpers for
refactored CentralNode commands.
"""

import json
import logging
import threading
import time
from datetime import datetime
from typing import Any, Optional, Tuple

from ska_tango_base.commands import ResultCode
from ska_tango_base.faults import CommandError, ResultCodeError
from ska_tango_base.long_running_commands.api import invoke_lrc
from ska_tmc_common import TimeoutCallback
from ska_tmc_common.adapters import AdapterFactory, AdapterType
from ska_tmc_common.v4.command_context import DeviceCommand
from ska_tmc_common.v4.tmc_command import BaseTMCCommand

from ska_tmc_centralnode.commands.central_node_command import (
    task_callback_default,
)
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
        self.logger = logger or LOGGER
        self._adapter_factory = adapter_factory or AdapterFactory()
        self.timeout_id = f"{time.time()}_{self.__class__.__name__}"
        self.timeout_callback = TimeoutCallback(self.timeout_id, self.logger)
        self.task_callback = task_callback_default
        self.mccs_mln_adapter = None
        self.command_subs_list = []
        self.command_results = {}
        self.command_device_id_map = {}
        self.task_abort_event = threading.Event()
        self.tm_subarray_adapter = None
        self.subarray_devname = ""
        self.dish_adapters = []
        self.subarray_adapters = []
        self.command_id = ""
        self.command_runtime_context: Any = None
        get_assign_context = getattr(
            self.component_manager, "_get_assign_context", None
        )
        if callable(get_assign_context):
            try:
                self.command_runtime_context = get_assign_context(command=self)
            except TypeError:
                self.command_runtime_context = get_assign_context()
        super().__init__(
            self.command_runtime_context,
            self._adapter_factory,
            self.logger,
        )

    def init_adapters(self) -> Tuple[ResultCode, str]:
        """Initialise adapters for MID or LOW command execution."""
        if isinstance(
            self.component_manager.input_parameter, InputParameterMid
        ):
            return self.init_adapters_mid()
        return self.init_adapters_low()

    def invoke_command(
        self,
        adapters: list,
        err_msg: str,
        command_name: str,
        argin: Optional[str] = None,
        callback=None,
    ) -> Tuple[list[ResultCode | Any], list[str | Any]]:
        """Invoke a command on adapters using CN long-running flow."""
        return_codes = []
        message_or_unique_ids = []

        for adapter in adapters:
            try:
                (
                    return_code,
                    message,
                ) = self.invoke_command_and_add_tracking_data(
                    adapter=adapter,
                    command_name=command_name,
                    command_input=argin,
                    callback=callback,
                )
                return_codes.append(return_code)
                message_or_unique_ids.append(message)
                self.logger.debug(
                    "Command invoked | command=%s device=%s",
                    command_name,
                    adapter.dev_name,
                )

            except Exception as exception:
                return_codes.append(ResultCode.FAILED)
                message_or_unique_ids.append(
                    f"{err_msg} {adapter.dev_name}: {exception}"
                )
                self.logger.error(
                    "Error in invoking %s on %s, Exception: %s",
                    command_name,
                    adapter.dev_name,
                    str(exception),
                )
        self.logger.debug(
            "Command responses received | command=%s responses=%s",
            command_name,
            str(message_or_unique_ids),
        )
        return return_codes, message_or_unique_ids

    def invoke_command_and_add_tracking_data(
        self, adapter, command_name, command_input=None, callback=None
    ):
        """Invoke CN LRC command and track the subscription data."""
        try:
            if not callback:
                callback = self.invoke_command_lrc_cb
            lrc_data = invoke_lrc(
                callback(adapter.dev_name),
                adapter._proxy,
                command_name,
                command_args=(command_input,) if command_input else None,
                logger=self.logger,
            )
            self.command_subs_list.append(lrc_data)
        except CommandError as exception:
            self.logger.error("command error %s", str(exception))
            error_message = (
                f"Command Error for device {adapter.dev_name}: "
                f"{str(exception)}"
            )
            return ResultCode.REJECTED, error_message
        except ResultCodeError as exception:
            self.logger.error("ResultCode error %s", str(exception))
            error_message = (
                f"error occurred for device {adapter.dev_name}: "
                f"{str(exception)}"
            )
            return ResultCode.FAILED, error_message
        return ResultCode.OK, ""

    def wait_for_command_completion(
        self,
        device_length: int,
        desired_state=None,
        function_name=None,
        use_command_class_id=False,
    ) -> Tuple[ResultCode, str]:
        """Wait for CN command completion and target state."""
        end_time = time.monotonic() + self.component_manager.command_timeout
        self.logger.debug(
            "Command subscription list %s", self.command_subs_list
        )
        with self.component_manager.command_completion_cond:
            while True:
                self._log_command_progress(device_length)
                wait_result = self._evaluate_completion_progress(
                    device_length,
                    desired_state,
                    function_name,
                    use_command_class_id,
                )
                if wait_result is not None:
                    return wait_result

                remaining = end_time - time.monotonic()
                timeout_result = self._handle_wait_timeout(
                    remaining, function_name, use_command_class_id
                )
                if timeout_result is not None:
                    return timeout_result

                self.component_manager.command_completion_cond.wait(remaining)

    def _log_command_progress(self, device_length: int) -> None:
        """Log command completion progress."""
        self.logger.debug(
            "Command progress | received=%s/%s",
            len(self.command_results.keys()),
            self.command_results,
        )
        self.logger.debug("Device length: %s", device_length)

    def _evaluate_completion_progress(
        self,
        device_length: int,
        desired_state=None,
        function_name=None,
        use_command_class_id=False,
    ) -> Tuple[ResultCode, str] | None:
        """Evaluate current completion status and return final result."""
        all_results_ok, failure_message = self._all_results_ok(device_length)
        if failure_message is not None:
            return ResultCode.FAILED, failure_message
        self.logger.debug("function_name %s %s", function_name, all_results_ok)
        if not all_results_ok:
            return None
        if not function_name:
            return ResultCode.OK, "Command Completed"

        state = self._get_wait_state(function_name, use_command_class_id)
        if state == desired_state:
            return ResultCode.OK, "Command Completed"
        return None

    def _all_results_ok(self, device_length: int) -> tuple[bool, str | None]:
        """Return completion status and any failure message."""
        if len(self.command_results.keys()) != device_length:
            return False, None

        failed_results_info = self._get_failed_results()
        if failed_results_info:
            return False, self._build_failure_message(failed_results_info)
        return True, None

    def _get_failed_results(self) -> dict:
        """Collect device results that are not successful."""
        failed_results_info = {}
        for device, result in self.command_results.items():
            self.logger.info(result)
            if result[0] != ResultCode.OK:
                failed_results_info[device] = result
        return failed_results_info

    def _build_failure_message(self, failed_results: dict) -> str:
        """Build a CN failure message from failed device results."""
        exception_message = "Exception occurred on the following devices: "
        for devname, error_value in sorted(failed_results.items()):
            _, error_message = error_value
            exception_message += f"{devname}: {error_message}"
        return exception_message

    def _get_wait_state(self, function_name, use_command_class_id):
        """Return the current state used by wait_for_command_completion."""
        if use_command_class_id:
            return getattr(self, function_name)()
        return getattr(self.component_manager, function_name)()

    def _handle_wait_timeout(
        self,
        remaining: float,
        function_name=None,
        use_command_class_id=False,
    ) -> Tuple[ResultCode, str] | None:
        """Handle timeout branch for completion waiting."""
        if remaining > 0:
            return None

        data = None
        if function_name:
            data = self._get_wait_state(function_name, use_command_class_id)
        self.logger.warning(
            "No event command results | command=%s state=%s",
            self.command_results,
            data,
        )
        return ResultCode.FAILED, "Timeout has occurred, command failed"

    def invoke_command_lrc_cb(self, device_name: str):
        """Create CN long-running-command callback."""

        def callback(result=None, **kwargs):
            del kwargs
            self.logger.debug(
                "Received command result %s from device %s",
                result,
                device_name,
            )
            if result:
                with self.component_manager.command_completion_cond:
                    self.command_results[device_name] = result
                    condition = self.component_manager.command_completion_cond
                    with condition:
                        condition.notify_all()

        return callback

    def set_command_id(self, command_name: str) -> None:
        """Set command id for CN error propagation and tracking."""
        self.command_id = f"{time.time()}-{command_name}"
        self.logger.info(
            "Setting command id as %s for command: %s",
            self.command_id,
            command_name,
        )

    def get_subarray_adapter(self, subarray_id: int) -> Tuple[ResultCode, str]:
        """Obtain adapter for a target subarray."""
        subarray_adapter_dev_name = (
            self.component_manager.subarray_trl_prefix
            + str(subarray_id).zfill(2)
        )

        self.logger.debug(
            "Command ID: %s | Attempting to get adapter for Subarray: %s",
            self.command_id,
            subarray_adapter_dev_name,
        )

        for adapter in self.subarray_adapters:
            if adapter.dev_name == subarray_adapter_dev_name:
                self.tm_subarray_adapter = adapter
                self.subarray_devname = adapter.dev_name
                return ResultCode.OK, ""

        return (
            ResultCode.FAILED,
            f"Subarray Id {subarray_id}({subarray_adapter_dev_name}) is"
            " not existing!",
        )

    def init_adapters_mid(self) -> Tuple[ResultCode, str]:
        """Initialise MID adapters required for AssignResources."""
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
                        ADAPTER_INIT_ERROR,
                        dev_name,
                        str(exception),
                    )
                    error_dev_names.append(dev_name)

        if num_working == 0:
            faulty_dev = ".".join(error_dev_names)
            message = f"Error in creating tm subarray adapters {faulty_dev},"
            return ResultCode.FAILED, message

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
                        ADAPTER_INIT_ERROR,
                        dev_name,
                        str(exception),
                    )
                    error_dev_names.append(dev_name)

        if num_working == 0:
            return (
                ResultCode.FAILED,
                f"Error in creating dish adapters {'.'.join(error_dev_names)}",
            )

        return ResultCode.OK, ""

    def init_adapters_low(self) -> Tuple[ResultCode, str]:
        """Initialise LOW adapters required for AssignResources."""
        self.mccs_mln_adapter = None
        self.subarray_adapters = []

        try:
            self.mccs_mln_adapter = (
                self._adapter_factory.get_or_create_adapter(
                    self.component_manager.input_parameter.mccs_mln_dev_name,
                    AdapterType.MCCS_MASTER_LEAF_NODE,
                )
            )
        except Exception as exception:
            return ResultCode.FAILED, str(exception)

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
                        ADAPTER_INIT_ERROR,
                        dev_name,
                        str(exception),
                    )
                    error_dev_names.append(dev_name)

        if num_working == 0:
            faulty_dev = ".".join(error_dev_names)
            message = f"Error in creating tm subarray adapters {faulty_dev},"
            return ResultCode.FAILED, message

        return ResultCode.OK, ""

    def put_result_in_command_mapping_dict(
        self, return_codes, message_or_unique_ids
    ) -> Tuple[ResultCode, str]:
        """Update CN command mapping using command invocation results."""
        for return_code, message_or_unique_id in zip(
            return_codes, message_or_unique_ids
        ):
            if return_code in [ResultCode.FAILED, ResultCode.REJECTED]:
                return ResultCode.FAILED, message_or_unique_id

            if return_code in [ResultCode.QUEUED, ResultCode.OK]:
                if self.component_manager.command_mapping.get(self.command_id):
                    self.logger.debug(
                        "Command ID: %s | Adding the ID %s to the command "
                        "mapping dictionary under command_id: %s",
                        self.command_id,
                        message_or_unique_id,
                        self.command_id,
                    )
                    self.component_manager.command_mapping[
                        self.command_id
                    ].append(message_or_unique_id)
                else:
                    self.logger.debug(
                        "Command ID: %s | Creating a command mapping "
                        "dictionary for id: %s, with unique_id: %s",
                        self.command_id,
                        self.command_id,
                        message_or_unique_id,
                    )
                    self.component_manager.command_mapping[self.command_id] = [
                        message_or_unique_id
                    ]
        return ResultCode.OK, ""

    def _update_event_callback(
        self, device_name: str, command_id: str, result: str
    ) -> None:
        """Update command result event data for a device."""
        if result:
            self.logger.debug(
                "Got command result for %s: %s", device_name, result
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
        """Update runtime event data storage and notify waiters."""
        if timestamp is None:
            timestamp = datetime.now()

        if self.command_runtime_context is None:
            return

        event_manager = self.command_runtime_context.get_evt_data_manager()
        event_manager.update_event_data(
            device=device_name,
            data=(
                command_id,
                result,
            ),
            received_timestamp=timestamp,
            data_type=data_type,
        )
        condition = self.context.completion_condition
        with condition:
            condition.notify_all()

    def command_invoked_callback(self, cmd_ctx: DeviceCommand) -> None:
        """Process command details after invocation."""
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
        """Set subarray obsstate to FAULT when timeout occurs."""
        if self.command_runtime_context is not None:
            self.command_runtime_context.obs_state_ctx.change_callback(
                {"component_obsfault": None}
            )
