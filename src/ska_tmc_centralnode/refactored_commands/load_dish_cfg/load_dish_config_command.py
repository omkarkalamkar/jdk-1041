"""Commad class for Load_dish_config_command"""

import json
from typing import Tuple

from ska_control_model import TaskStatus
from ska_tango_base.commands import ResultCode
from ska_telmodel.data import TMData
from ska_tmc_common.adapter_type import AdapterType
from ska_tmc_common.v4.command_context import CommandResult, DeviceCommand
from ska_tmc_common.v4.tmc_command import BaseTMCCommand

from ska_tmc_centralnode.model.enum import DishConfigStatus
from ska_tmc_centralnode.utils.constants import (
    DISH_KVALUE_VALIDATION_RESULT_STATUS,
    DISH_VCC_VALIDATION_RESULT_STATUS,
    MID_CSP_MLN_DEVICE,
)

from .contexts import LoadDishCfgRuntimeContext
from .dish_k_executor import DishKValueExecutor
from .errors import DishAdapterError
from .load_dish_cfg_stragegy import LoadDishCfgStrategy


class LoadDishCfg(BaseTMCCommand):
    """
    A class for CentralNode's LoadDishConfig command.
    Load DishId-VCC map from CAR URI and provide it to Csp Master Leaf Node
    After Validation
    """

    command_name = "LoadDishCfg"

    def __init__(
        self,
        command_runtime_context: LoadDishCfgRuntimeContext,
        adapter_factory,
        logger,
        timeout_subarrays: int = 60,
        step_sleep: int = 1,
    ):
        super().__init__(command_runtime_context, adapter_factory, logger)
        self._timeout_subarrays = timeout_subarrays
        self._step_sleep = step_sleep
        self.dish_cfg_params: str = ""
        self.dish_vcc_config_json: dict = {}
        self.stragegy = LoadDishCfgStrategy(
            command_runtime_context, logger, self.context.command_id
        )
        self.plan = None
        # This is required to keep track of the
        # dish adapters for invoking SetKValue command
        self.adapter_factory = adapter_factory

    def prepare_command(self) -> None:
        """
        Prepare the command for execution.
        """
        self.plan = self.stragegy.build(self.context.argin)
        runtime_context = self.command_runtime_context
        runtime_context.command_ctx.update_command_in_progress_id(
            "LoadDishCfg"
        )
        runtime_context.command_ctx.set_load_dish_cfg_aggregated_result(False)
        runtime_context.command_ctx.set_dish_vcc_command_status(
            DishConfigStatus.IN_PROGRESS
        )

    def build_device_commands(self) -> None:
        """
        Build the device commands for execution.
        """
        runtime = self.command_runtime_context
        self.context.device_commands = [
            DeviceCommand(
                device_name=runtime.device_ctx.csp_mln_device_name,
                adapter_type=AdapterType.CSP_MASTER_LEAF_NODE,
                command_name="LoadDishCfg",
                command_input=self.plan.dish_cfg_params,
            )
        ]

    def invoke(self) -> None:
        """
        Invoke the command on the devices.
        """
        self.logger.debug(
            "Command ID: %s | Invoking LoadDishCfg command",
            self.context.command_id,
        )
        super().invoke()
        self._execute_on_dish()

    def _execute_on_dish(self):
        """
        Execute kvalue on Dish
        """
        dish_adapters = self.get_dish_adapters()
        kval_aggregator = self.command_runtime_context.update_kval_aggregator
        dish_kvalue_executor = DishKValueExecutor(
            dish_adapters=dish_adapters,
            command_id=self.context.command_id,
            invoke_callback_factory=self.async_cb,
            add_device_command=self.context.device_commands.append,
            add_device_name=self.command_runtime_context.append_dish_dev_names,
            update_kvalue_aggregator=kval_aggregator,
            logger=self.logger,
        )
        dish_kvalue_executor.execute(self.plan.dish_parameters)

    def update_task_status(
        self, result: Tuple[ResultCode, str], exception: str = ""
    ) -> None:
        """
        Updates the task status for command

        Args:
            result: Result code of command
            exception (str): any message returned as a part of command

        """
        runtime_context = self.command_runtime_context
        aggregator = runtime_context.dish_kvalue_validation_aggregator
        k_val_results = aggregator.dln_kvalue_validation_results
        self.logger.debug(
            "Task callback invoked | command=LoadDishCfg id=%s result=%s "
            "message=%s",
            self.context.command_id,
            str(result[0]),
            exception,
        )
        result = self.process_loaddishcfg_as_per_err_message_or_exception(
            result=result,
            k_val_results=k_val_results,
            exception=exception,
        )
        self.logger.info("Result is %s", result)
        if result[0] == ResultCode.FAILED or result[2]:
            error_message = result[1] + " LoadDishCfg command failed: "
            self.command_runtime_context.command_ctx.update_dish_vcc_flag(
                False
            )
            self.process_update_task_for_loaddishcfg_failure(error_message)
        else:
            self.process_loaddishcfg_as_per_k_val_results(k_val_results)
            self.update_memorized_attribute()
        self.command_runtime_context.command_ctx.set_dish_vcc_command_status(
            DishConfigStatus.COMPLETED
        )
        # self.component_manager.reset_load_dish_cfg_data()

    def process_loaddishcfg_as_per_k_val_results(
        self, k_val_results: dict
    ) -> None:
        """
        Process the command output as per the k value validation results.

        Args:
            k_val_results (dict): Mapping of dish IDs or component names to
                their k-value validation result strings.
        """
        ok_status = DISH_KVALUE_VALIDATION_RESULT_STATUS[ResultCode.OK].lower()
        statuses = {v.lower() for v in k_val_results.values()}

        all_ok = statuses == {ok_status}
        partial_ok = not all_ok and ok_status in statuses

        message, result_code, dish_vcc_flag = self._build_loaddishcfg_outcome(
            all_ok, partial_ok
        )

        self.context.task_callback(
            status=TaskStatus.COMPLETED,
            result=(result_code, message),
            **(
                {"exception": message}
                if result_code == ResultCode.FAILED
                else {}
            ),
        )
        self.command_runtime_context.command_ctx.update_dish_vcc_flag(
            dish_vcc_flag
        )

    def _build_loaddishcfg_outcome(
        self, all_ok: bool, partial_ok: bool
    ) -> Tuple[str, ResultCode, bool]:
        """
        Derive the message, result code, and dish VCC flag
        from validation outcome.

        Args:
            all_ok (bool): True if every dish passed k-value validation.
            partial_ok (bool): True if only some dishes passed.

        Returns:
            Tuple[str, ResultCode, bool]: message, result code, dish_vcc_flag.
        """
        if all_ok:
            return "Command Completed", ResultCode.OK, True
        runtime_ctx = self.command_runtime_context
        failed_data = str(
            self.filter_failed_data(
                json.loads(
                    runtime_ctx.command_ctx.get_dish_vcc_validation_status()
                )
            )
        )

        if partial_ok:
            message = (
                f"LoadDishCfg completed with partial success: {failed_data}"
            )
            return message, ResultCode.OK, True

        message = f"LoadDishCfg failed: {failed_data}"
        return message, ResultCode.FAILED, False

    def process_loaddishcfg_as_per_err_message_or_exception(
        self,
        result: Tuple[ResultCode, str],
        k_val_results: dict,
        exception: str = "",
    ) -> Tuple[ResultCode, str, bool]:
        """
        Process result based on an error message or exception.

        Args:
            result (Tuple[ResultCode, str]): The original result code and
                message from the invoked commands.
            k_val_results (dict): Mapping of dish/component to k-value
                validation results.
            exception (str): Optional exception or error text.

        Returns:
            Tuple[ResultCode, str, bool]: Adjusted result code, message,
                and a flag indicating whether CSP failure occurred.
        """
        csp_failed, failed_count = self._collect_failed_kvalue_results(
            k_val_results
        )
        self.logger.info("Exception is %s", exception)
        if failed_count:
            self._persist_kvalue_validation_results(k_val_results)

        csp_failed = csp_failed or self._csp_validation_status_failed(
            failed_count
        )

        adjusted_result = self._adjust_result(result, exception, csp_failed)
        self.logger.info("Adjusted result %s", adjusted_result)
        return (*adjusted_result, csp_failed)

    def _collect_failed_kvalue_results(
        self, k_val_results: dict
    ) -> Tuple[bool, int]:
        """
        Iterate command results, collecting failures.

        Args:
            k_val_results (dict): k-value validation results mapping.

        Returns:
            Tuple[bool, int]: (csp_failed, non_csp_failure_count)
        """
        failed_count = 0
        is_cmd_failed_on_csp = False
        # cm = self.component_manager
        for device, result in self.context.results.items():
            dev_id = device.split("/")[2].lower()
            if result.result_code not in [
                ResultCode.FAILED,
                ResultCode.REJECTED,
                ResultCode.NOT_ALLOWED,
            ]:
                if "csp" not in device.lower():
                    msg = DISH_KVALUE_VALIDATION_RESULT_STATUS[ResultCode.OK]
                    if k_val_results.get(dev_id) != msg:
                        # with cm.dish_vcc_validation_attr_lock:
                        k_val_results[dev_id] = msg
            else:
                if "csp" in device.lower():
                    is_cmd_failed_on_csp = True
                    continue  # Skip CSP failures for k-value aggregation
                # with cm.dish_vcc_validation_attr_lock:
                k_val_results[dev_id] = result.message
                failed_count += 1
        return is_cmd_failed_on_csp, failed_count

    def _persist_kvalue_validation_results(self, k_val_results: dict) -> None:
        """Persist updated k-value validation results to component manager.

        Args:
         k_val_results (dict): k-value validation results mapping.
        """
        runtime_ctx = self.command_runtime_context
        # with self.component_manager.dish_vcc_validation_attr_lock:
        runtime_ctx.command_ctx.set_dish_vcc_validation_status(k_val_results)

    def _csp_validation_status_failed(self, failed_count: int) -> bool:
        """
        Check whether CSP MLN validation status is non-OK or all
        subscribed commands have failed.

        Args:
            failed_count: count for command failure on invoked devices.
        """
        runtime_ctx = self.command_runtime_context
        status = json.loads(
            runtime_ctx.command_ctx.get_dish_vcc_validation_status()
        )
        csp_status_not_ok = status.get(MID_CSP_MLN_DEVICE) != (
            DISH_VCC_VALIDATION_RESULT_STATUS[ResultCode.OK]
        )
        all_commands_failed = failed_count >= len(self.context.results)
        return csp_status_not_ok or all_commands_failed

    def _adjust_result(
        self,
        result: Tuple[ResultCode, str],
        exception: str,
        csp_failed: bool,
    ) -> Tuple[ResultCode, str]:
        """
        Determine the final result code and message based on the error
        type and whether a CSP failure occurred.

        Args:
            result (Tuple[ResultCode, str]): The original result code and
                message from the invoked commands.
            exception: Exception string.
            csp_failed (bool): Does command failed on CSP.
        """
        combined_text = f"{result[1]} {exception}".lower()

        if csp_failed:
            return result  # Preserve original FAILED result

        if "timeout" in combined_text:
            return ResultCode.OK, result[1]

        if "exception" in combined_text:
            return (
                ResultCode.FAILED if csp_failed else ResultCode.OK,
                result[1],
            )

        return ResultCode.OK, ""

    def process_update_task_for_loaddishcfg_failure(
        self, error_message: str
    ) -> None:
        """Method to update the task callback and loaddishcfg status
        with the failure data

        Args:
            error_message: Error message to be updated in task callback.
        """
        runtime_ctx = self.command_runtime_context
        error_message = error_message + str(
            self.filter_failed_data(
                json.loads(
                    runtime_ctx.command_ctx.get_dish_vcc_validation_status()
                )
            )
        )
        self.context.task_callback(
            status=TaskStatus.COMPLETED,
            result=(ResultCode.FAILED, error_message),
            exception=error_message,
        )

    def filter_failed_data(self, data: dict) -> dict:
        """Filter dish vcc data for failed dish and csp master.
        Args:
            data(dict): Dish and csp master data.
        Returns:
            dish dict
        """
        filtered = {}
        success_string = [
            "ALL DISH OK",
            "TMC and CSP Master Dish Vcc Version is Same",
        ]
        for tmc_component, content in data.items():
            if content in success_string:
                continue
            filtered[tmc_component] = content
        return filtered

    def update_memorized_attribute(self) -> None:
        """
        Update memorized attribute so after restart this
        attribute used to get dish map vcc version set before
        restart
        """
        runtime_ctx = self.command_runtime_context
        runtime_ctx.command_ctx.update_memorized_attribute(
            self.plan.dish_cfg_params
        )
        # self.csp_mln_adapter.memorizedDishVccMap = self.dish_cfg_params

    def get_dishid_vcc_map_json(
        self, initial_params: dict
    ) -> Tuple[dict, str]:
        """
        Get DishId-VCC map json from initial params

        Args:
            initial_param (dict): this param containg tm
                data source uri and file path which is used
                for extracting vcc_map json file

        Returns:
            Tuple(dict, str): tuple having `DishId-VCC map json` and
            `Error message` if any

        """
        data_sources = initial_params.get("tm_data_sources", None)
        tm_data_filepath = initial_params.get("tm_data_filepath", None)
        self.logger.debug(
            "Command ID: %s | The initial params are : %s",
            self.context.command_id,
            json.dumps(initial_params),
        )
        if data_sources and tm_data_filepath:
            try:
                data = TMData(data_sources)
                return data[tm_data_filepath].get_dict(), ""
            except Exception as exception:
                self.logger.exception(
                    "Command ID: %s |  Error in Loading Dish VCC map "
                    + "json file %s, retrying",
                    self.context.command_id,
                    exception,
                )
                return (
                    {},
                    f"Error in Loading Dish VCC map json file {exception}",
                )
        return {}, "tm_data_sources and tm_data_filepath not provided in json"

    def get_dish_adapters(self) -> list:
        """
        Get the list of dish adapters.

        Returns:
            list: List of dish adapters.
        """
        dish_adapters = []
        num_working = 0
        error_dev_names = []
        for (
            dev_name
        ) in self.command_runtime_context.device_ctx.dish_leaf_node_dev_names:
            devInfo = self.command_runtime_context.device_ctx.get_dev(dev_name)
            if not devInfo.unresponsive:
                try:
                    dish_adapters.append(
                        self.adapter_factory.get_or_create_adapter(
                            dev_name, AdapterType.DISH
                        )
                    )
                    num_working += 1
                    self.logger.debug(
                        "Adapter is created for DishLeafNode: %s", dev_name
                    )
                except Exception as e:
                    self.logger.exception(
                        "Exception in creating adapter for %s, Exception: %s",
                        dev_name,
                        str(e),
                    )
                    error_dev_names.append(dev_name)
        if num_working == 0:
            raise DishAdapterError(
                f"Error in creating dish adapters {'.'.join(error_dev_names)}"
            )
        return dish_adapters

    def async_cb(self, device_name: str):
        """Invoke LRC callback.
        Provide this callback whenever command is invoked using invoke_lrc api
        Args:
            device_name: Name Of Device
        Returns:
            callback: function object to provided to invoke_lrc
        """

        def callback(event_data):
            runtime_ctx = self.command_runtime_context
            if event_data:
                value = event_data.argout
                result = [value[0][0], value[1][0]]
                self.logger.debug(
                    "Event Value %s and Result: %s", value, result
                )
                with runtime_ctx.command_completion_condition:
                    self.context.results[device_name] = CommandResult(
                        device_name=device_name,
                        result_code=result[0],
                        message=result[1],
                    )
                    cond = runtime_ctx.command_completion_condition
                    with cond:
                        cond.notify_all()

        return callback
