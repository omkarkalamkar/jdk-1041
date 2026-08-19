"""SetGlobalPointing command module.

This module provides functions to execute the SetGlobalPointing command
on the Dishes.
"""

import json
import logging
from typing import Any, Callable, List, Optional, Tuple

from ska_control_model import ResultCode, TaskStatus
from ska_telmodel.data import TMData
from ska_tmc_common import AdapterFactory
from ska_tmc_common.adapter_type import AdapterType
from ska_tmc_common.exceptions import InvalidReceptorIdError
from ska_tmc_common.v4.command_context import CommandResult, DeviceCommand
from ska_tmc_common.v4.tmc_command import BaseTMCCommand

from ska_tmc_centralnode.refactored_commands.set_gpm.gpm_json_model import (
    GPMJsonModel,
)

from .contexts import GPMContext, GPMRequest
from .strategy import GPMPlan


class SetGlobalPointingModel(BaseTMCCommand):
    """A class to execute the SetGlobalPointingModel command for MID.

    Executes ApplyPointingModel command on Dish.
    """

    def __init__(
        self,
        command_runtime_context: GPMContext,
        adapter_provider: AdapterFactory,
        logger: logging.Logger,
    ) -> None:
        """Initializes the GPM command class for Mid telescope.

        :param command_runtime_context: GPM command context.
        :type command_runtime_context: GPMContext
        :param adapter_provider: Instance of adapter factory to fetch adapters.
        :type adapter_provider: AdapterFactory
        :param logger: Instance of logger.
        :type logger: logging.Logger
        """
        super().__init__(command_runtime_context, adapter_provider, logger)
        self.command_runtime_context: GPMContext = command_runtime_context
        self.adapter_provider: AdapterFactory = adapter_provider
        self.result_code: ResultCode = ResultCode.UNKNOWN
        self.command_name: str = self.__class__.__name__
        self._plan: GPMPlan = GPMPlan({})
        self.error_message: str = ""

    def pre_process(self, argin: Optional[Any] = None) -> None:
        """Pre-process the SetGlobalPointingModel command.

        :param argin: Command input data.
        :type argin: Optional[Any]
        :return: None
        :rtype: None
        """
        self.command_runtime_context.update_name(self.__class__.__name__)
        self.logger.debug("Received GPM Input: %s", argin)

    def _build_device_command(
        self,
        device_name: str,
        callback: Callable,
        command_input: str | None = None,
    ) -> DeviceCommand:
        """Build a device-specific command.

        :param device_name: Name of the target device.
        :type device_name: str
        :param callback: Callback invoked for command events.
        :type callback: callable
        :param command_input: Optional input for the command.
        :type command_input: str | None
        :return: Device-specific command instance.
        :rtype: DeviceCommand
        """
        kwargs = {
            "device_name": device_name,
            "command_name": "ApplyPointingModel",
            "command_input": command_input,
            "adapter_type": AdapterType.DISH,
            "update_event_callback": callback,
        }
        return DeviceCommand(**kwargs)

    def build_device_commands(self) -> None:
        """Method to build the device specific command details."""
        try:
            device_commands = []
            ctx = self.command_runtime_context
            dish_leaf_node_dev_names = ctx.get_dish_leaf_node_device_names()
            for dish_id, gpm_inputs in self._plan.apm_payload.items():
                dish_dev_name = next(
                    name
                    for name in dish_leaf_node_dev_names
                    if dish_id in name
                )
                ctx.dishln_gpm_cmd_exe_data.setdefault(dish_id, {})
                for apm_input in gpm_inputs:
                    tm_data_filepath = apm_input["tm_data_filepath"]
                    dishln_band = (
                        tm_data_filepath.split("/")[-1]
                        .split("-")[-1]
                        .split(".")[0]
                    )
                    callback = self.update_set_gpm_results(
                        band_value=dishln_band
                    )
                    device_commands.append(
                        self._build_device_command(
                            device_name=dish_dev_name,
                            callback=callback,
                            command_input=json.dumps(apm_input),
                        )
                    )
            self.context.device_commands = device_commands
        except Exception:
            self.logger.exception(
                "Exception occurred while building device commands"
                " for SetGlobalPointingModel command"
            )

    def update_set_gpm_results(self, band_value: str) -> callable:
        """Create a callback to update SetGlobalPointingModel results.

        :param band_value: Band value associated with the callback.
        :type band_value: str
        :return: Callback function for processing result events.
        :rtype: callable
        """

        def callback(dev_name: str, command_id: str, result: str):
            result = json.loads(result)
            if self.context.results.get(dev_name):
                del self.context.results[dev_name]

            self.context.results[dev_name + band_value] = CommandResult(
                device_name=dev_name,
                result_code=result[0],
                message=result[1],
                command_id=command_id,
            )
            self.logger.debug(
                "GPM longRunningCommandResult event for device: "
                "%s, with value: %s",
                dev_name,
                str(result),
            )
            with self.command_runtime_context.dishln_gpm_lock:
                ctx = self.command_runtime_context
                dishln_id = dev_name.split("/")[-1]
                if result:
                    if dishln_id in ctx.dishln_gpm_cmd_exe_data:
                        ctx.dishln_gpm_cmd_exe_data[dishln_id][
                            band_value
                        ] = result
                        self.logger.debug(
                            "Dishln gpm current status: %s",
                            ctx.dishln_gpm_cmd_exe_data,
                        )

        return callback

    def _build_gpm_plan(
        self, gpm_request: GPMRequest, gpm_files=None
    ) -> GPMPlan:
        """Build the SetGlobalPointingModel execution plan.

        :param gpm_request: SetGlobalPointingModel request data.
        :type gpm_request: GPMRequest
        :param gpm_files: List of GPM files.
        :type gpm_files: list, optional
        :return: SetGlobalPointingModel execution plan.
        :rtype: GPMPlan
        """
        strategy = self.command_runtime_context.make_strategy(self.logger)
        gpm_data, no_gpm_files_found = strategy.build_plan(
            gpm_request, gpm_files
        )
        if no_gpm_files_found:
            for dish_id, error in no_gpm_files_found.items():
                self.add_data_to_gpm_dictionary_in_case_of_error(
                    dish_id, error
                )
        return gpm_data

    def prepare_command(self) -> None:
        """Prepare GPM request and execution plan."""

        self.command_runtime_context.update_abort_evt(
            self.context.task_abort_event
        )
        if not isinstance(self.context.argin, str):
            raise ValueError("GPM input argument is required")
        gpm_paths = self.command_runtime_context.default_gpm_version_params
        if any(value in (None, "") for value in gpm_paths.values()):
            self.error_message = "GPM Telmodel paths not set."
            self.logger.exception("%s:  %s", self.error_message, gpm_paths)
            raise ValueError(self.error_message)
        request = GPMRequest.from_json(self.context.argin)
        if "receptors" not in request.data:
            ctx = self.command_runtime_context
            self.error_message = "No GPM files found on set GPM parameters."
            gpm_files = self.get_gpm_files(ctx.default_gpm_version_params)
            if not gpm_files:
                self.logger.error("Error message: %s", self.error_message)
                self.result_code = ResultCode.FAILED
            else:
                self._plan = self._build_gpm_plan(request, gpm_files)
        else:
            self._plan = self._build_gpm_plan(request)
        self.validate_dishes(self._plan.apm_payload)

    def validate_gpm_keys(self, request: dict) -> None:
        """Validate the required keys in the GPM request.

        :param request: GPM request data to validate.
        :type request: dict
        :return: None.
        :rtype: None
        """

        keys_allowed_to_skip = [
            "version",
            "tm_data_filepath",
            "tm_data_sources",
            "interface",
        ]

        if not all(key in request for key in keys_allowed_to_skip):
            GPMJsonModel(**request)
            if not GPMJsonModel.validate_dish_ids(request["receptors"].keys()):
                raise InvalidReceptorIdError(
                    f"Incorrect receptor id in json: {request}"
                )
        else:
            self.logger.debug(
                "Executing initialization/restart SetGPM on %s",
                self.command_runtime_context.gpm_unknown_dishes,
            )

    def get_gpm_files(self, initial_params: dict) -> list:
        """Get GPM files from the initial parameters.

        :param initial_params: Parameters containing the TM data source URI
            and file path used to retrieve GPM files.
        :type initial_params: dict
        :return: List of GPM file names found in the data repository.
        :rtype: list
        """

        gpm_files: List[str | None] = []
        data_sources = initial_params.get("tm_data_sources", [])[0]
        tm_data_filepath = initial_params.get("tm_data_filepath", "")
        data_sources = (
            data_sources
            + "?"
            + initial_params.get("version", None)
            + "#tmdata"
        )
        self.logger.debug(
            "Command ID: %s| The initial params are :  %s",
            self.context.command_id,
            initial_params,
        )
        if data_sources and tm_data_filepath:
            try:
                tmdata = TMData([data_sources])
                gpm_path = tmdata[tm_data_filepath]
                gpm_files = list(gpm_path)
                return gpm_files
            except Exception as exception:
                self.logger.exception(
                    "Command ID: %s |  Error in Loading GPM "
                    + "json file %s,",
                    self.context.command_id,
                    exception,
                )
                self.error_message = f"Error in fetching GPM file {exception}"

        self.error_message = (
            "tm_data_sources and tm_data_filepath not provided in json"
        )
        return gpm_files

    def validate_dishes(self, gpm_data: dict) -> None:
        """Validate dish availability and subarray assignment.

        :param gpm_data: GPM data keyed by dish ID.
        :type gpm_data: dict
        :return: None
        :rtype: None
        """

        ctx = self.command_runtime_context
        for dish_id in list(gpm_data):
            error_message = None
            dish_trl = f"{ctx.dish_leaf_node_prefix}/{dish_id}"
            try:
                dish_info = ctx.get_device(dish_trl)
                if not dish_info or dish_info.unresponsive:
                    error_message = "Dish is unreachable"
                elif ctx.is_already_assigned(
                    dish_id.upper()
                ) or ctx.is_already_assigned(dish_id.lower()):
                    error_message = "Dish is assigned to subarray"
            except Exception:
                error_message = "Dish is unreachable"
                self.logger.exception(error_message)
            if error_message:
                self.result_code = ResultCode.FAILED
                self.add_data_to_gpm_dictionary_in_case_of_error(
                    dish_id, error_message
                )
                self.logger.error("%s: %s", dish_id, error_message)
                gpm_data.pop(dish_id)

    def add_data_to_gpm_dictionary_in_case_of_error(
        self, dish_id: str, error_message: str
    ) -> None:
        """Add an error message to the GPM data for a dish.

        :param dish_id: Dish leaf node identifier.
        :type dish_id: str
        :param error_message: Error message to add.
        :type error_message: str
        :return: None
        :rtype: None
        """
        if dish_id not in self.command_runtime_context.dishln_gpm_cmd_exe_data:
            self.command_runtime_context.dishln_gpm_cmd_exe_data[dish_id] = {}
        self.command_runtime_context.dishln_gpm_cmd_exe_data[dish_id] = (
            "ERROR: " + error_message
        )

    # pylint: disable=arguments-differ
    def update_task_status(
        self,
        result: tuple = (),
        status: TaskStatus = TaskStatus.COMPLETED,
        message: str = "",
        exception: str = "",
    ) -> None:
        """Update task status with result and exception information.

        :param result: Tuple containing the result code and unique ID.
        :type result: tuple
        :param status: Current task status.
        :type status: TaskStatus
        :param message: Failure or exception message.
        :type message: str
        :param exception: Exception information, if any.
        :type exception: str
        :return: None
        :rtype: None
        """
        msg: str = message or exception
        self.logger.info(
            "Command ID: %s | Received task status with Result: %s",
            self.command_runtime_context.get_name(),
            (result, status, msg),
        )
        self.result_code = list(result)[0]
        self.process_update_task_status()

    def process_update_task_status(self) -> None:
        """Update the task callback and GPM status with the failure data."""
        ctx = self.command_runtime_context

        message = (
            self._build_gpm_status_message(ctx)
            if ctx.dishln_gpm_cmd_exe_data
            else self.error_message
        )

        if self.error_message:
            self.result_code = ResultCode.FAILED

        result = (self.result_code, message)
        self.logger.info(
            "Command ID: %s | Updating task status with Result: %s",
            self.context.command_id,
            result,
        )

        callback_kwargs = {"result": result, "status": TaskStatus.COMPLETED}
        if self.result_code != ResultCode.OK:
            callback_kwargs["exception"] = message
        self.context.task_callback(**callback_kwargs)

        ctx.reset_gpm_data()

    # pylint: enable=arguments-differ

    def _build_gpm_status_message(self, ctx) -> str:
        """Update GPM status and build the failure message.

        Skips statuses for unreachable or assigned dishes.

        :param ctx: Runtime context containing GPM execution data.
        :type ctx: CommandRuntimeContext
        :return: GPM status or failure message.
        :rtype: str
        """

        skip_status_markers: Tuple[str, str] = (
            "Dish is assigned to subarray",
            "Dish is unreachable",
        )

        for dish_id, result in ctx.dishln_gpm_cmd_exe_data.items():
            if isinstance(result, str) and not any(
                marker in result for marker in skip_status_markers
            ):
                ctx.global_pointing_model_status[dish_id] = result

        filtered_dishes = (
            self.filter_failed_dish_data(ctx.dishln_gpm_cmd_exe_data)
            or ctx.dishln_gpm_cmd_exe_data
        )

        prefix = (
            "SetGPM failed on: " if self.result_code != ResultCode.OK else ""
        )
        if prefix:
            return prefix + str(filtered_dishes)
        return str(filtered_dishes)

    def filter_failed_dish_data(self, data: dict) -> dict:
        """Filter failed dish data.

        :param data: Dish data to filter.
        :type data: dict
        :return: Filtered dish data.
        :rtype: dict
        """

        filtered = {}
        for dish, content in data.items():
            if isinstance(content, dict):
                bands = {}
                for band, value in content.items():
                    if value and value[0] != 0:
                        self.result_code = ResultCode.FAILED
                        bands[band] = value
                if bands:
                    filtered[dish] = bands
            else:
                self.result_code = ResultCode.FAILED
                filtered[dish] = content
        return filtered

    def post_process(self) -> None:
        """Post-processing of scan command."""
        self.command_runtime_context.clear()

    def clear_device_events(self) -> None:
        """Method to clean up the device event data."""
        self.command_runtime_context.clear()
