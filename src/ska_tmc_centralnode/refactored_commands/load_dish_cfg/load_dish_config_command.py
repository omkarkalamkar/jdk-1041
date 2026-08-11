"""Commad class for Load_dish_config_command"""

import json
from typing import Tuple

from retry import retry
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
from .errors import DishAdapterError, SetKValueError
from .load_dish_cfg_stragegy import LoadDishCfgStrategy


# pylint:disable =abstract-method
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
                update_event_callback=self._update_event_callback,
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
        self._set_k_numbers_to_dish(self.plan.dish_parameters)

    def _update_event_callback(
        self, device_name: str, command_id: str, result: str
    ) -> None:
        """
        Callback to handle command events.

        Args:
            device_name (str): Name of the device.
            command_id (str): ID of the command.
            result (str): Result of the command.
        """
        self.logger.debug(
            "Command ID: %s | Device: %s | Result: %s",
            command_id,
            device_name,
            result,
        )
        # Here you can implement any additional logic needed to handle
        # the command result, such as updating internal state or
        # notifying other components.

    # def set_command_id(self, command_name: str) -> None:
    #     """Sets the command id for error propagation.
    #
    #     :param command_name: name of the command.
    #     :type command_name: str
    #     """
    #     self.command_id = f"{time.time()}-{command_name}"
    #     self.logger.info(
    #         "Setting command id as %s for command: %s",
    #         self.command_id,
    #         command_name,
    #     )
    #     self.component_manager.command_id = self.command_id

    # def load_dish_cfg(
    #     self,
    #     argin: str,
    #     task_callback,
    #     task_abort_event,
    # ) -> Tuple[ResultCode, str]:
    #     """
    #     Load Dish Configuration command.
    #     Validates dish-vcc data, executes lower-level command.
    #
    #     Args:
    #         argin (str): Input argument for the command.
    #
    #     Returns:
    #         Tuple(ResultCode, str): Result code and message.
    #
    #     """
    #     self.component_manager.command_in_progress = "LoadDishCfg"
    #     self.component_manager.load_dish_cfg_aggregated_result = False
    #     self.task_callback = task_callback
    #     self.task_abort_event = task_abort_event
    #     self.component_manager.abort_event = self.task_abort_event
    #     self.task_callback(status=TaskStatus.IN_PROGRESS)
    #
    #     # Set Dish-specific command status
    #     self.component_manager.dish_vcc_command_status = (
    #         DishConfigStatus.IN_PROGRESS
    #     )
    #
    #     # # Validate
    #     (
    #         dish_vcc_map_json,
    #         error_message,
    #     ) = self.check_and_validate_dish_vcc_data(argin)
    #     if error_message:
    #         self.component_manager.dish_vcc_validation_status = {
    #             CENTRALNODE_MID: error_message
    #         }
    #         self.update_task_status(
    #             result=(ResultCode.FAILED, error_message),
    #             exception=error_message,
    #         )
    #         return ResultCode.FAILED, error_message
    #
    #     # Save validated config
    #     self.dish_vcc_config_json = dish_vcc_map_json
    #     self.dish_cfg_params = argin
    #
    #     # Execute device-level command
    #     self.component_manager.load_dish_cfg_command_id = self.command_id
    #     result, message = self.do(argin)
    #     self.update_task_status(result=(result, message), exception=message)
    #     return result, message

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
        if result[0] == ResultCode.FAILED or result[2]:
            error_message = result[1] + " LoadDishCfg command failed: "
            self.command_runtime_context.command_ctx.update_dish_vcc_flag(
                False
            )
            self.process_update_task_for_loaddishcfg_failure(error_message)
        else:
            self.process_loaddishcfg_as_per_k_val_results(k_val_results)
            self.update_memorized_attribute()
        # if self.component_manager.command_mapping.get(self.command_id):
        #     self.component_manager.command_mapping.pop(self.command_id)
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

        if failed_count:
            self._persist_kvalue_validation_results(k_val_results)

        csp_failed = csp_failed or self._csp_validation_status_failed(
            failed_count
        )

        adjusted_result = self._adjust_result(result, exception, csp_failed)

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
        for device, (
            result_code,
            message,
        ) in self.context.command_device_ids.items():
            dev_id = device.split("/")[2].lower()
            if result_code not in [
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
                k_val_results[dev_id] = message
                failed_count += 1
        return is_cmd_failed_on_csp, failed_count

    def _persist_kvalue_validation_results(self, k_val_results: dict) -> None:
        """Persist updated k-value validation results to component manager.

        Args:
         k_val_results (dict): k-value validation results mapping.
        """
        runtime_ctx = self.command_runtime_context
        # with self.component_manager.dish_vcc_validation_attr_lock:
        runtime_ctx.set_dish_vcc_validation_status(k_val_results)

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

    # pylint:disable=signature-differs
    # def do(self, argin: str) -> Tuple[ResultCode, str]:
    #     """
    #     This command performs the following steps:\n
    #     1. Loads the content of the DishId-VCC mapping file from CAR URI.\n
    #     2. Validates the JSON.\n
    #     3. Invokes a command on the CSP master leaf node.\n
    #     4. Invokes the SetKValue
    #     command on the Dish Leaf Node for each dish ID
    #     provided in the DishId-VCC map.\n
    #
    #     Args:
    #         argin (str): DishId-VCC map parameters in JSON string format.
    #
    #     Returns:
    #         Tuple(ResultCode, str): Result code and message
    #
    #     """
    #     self.set_command_id(self.__class__.__name__)
    #     self.logger.debug(
    #         "Command %s: Executing LoadDishCfg command",
    #         self.command_id,
    #     )
    #
    #     result_code, message = self.init_adapters()
    #     if result_code == ResultCode.FAILED:
    #         self.logger.error(
    #             "Adapter initialization failed | command_id=%s error=%s",
    #             self.command_id,
    #             message,
    #         )
    #         if "Error in creating dish adapters" in message:
    #             cm = self.component_manager
    #             aggregator = cm.dish_kvalue_validation_aggregator
    #             val_results = aggregator.dln_kvalue_validation_results
    #             val_results.clear()
    #             val_results[
    #                 "dish"
    #             ] = "No Dish Leaf Node found to invoke SetKValue command"
    #             self.component_manager.
    #             dish_vcc_validation_status = val_results
    #             self.logger.debug(
    #                 "Dish aggregator: %s CSP Dish aggregator: %s",
    #                 val_results,
    #                 self.component_manager.dish_vcc_validation_status,
    #             )
    #         return result_code, message
    #
    #     dishid_vcc_map_params = json.loads(argin)
    #     self.logger.debug(
    #         "DishId-VCC map parameters | command_id=%s params=%s",
    #         self.command_id,
    #         json.dumps(dishid_vcc_map_params),
    #     )
    #
    #     dish_parameters = self.dish_vcc_config_json.get("dish_parameters")
    #
    #     for return_codes, message_or_unique_ids in [
    #         self._invoke_load_dish_cfg_on
    #         _csp_master_ln(dishid_vcc_map_params),
    #         self._set_k_numbers_to_dish(dish_parameters),
    #     ]:
    #         for return_code, message_or_unique_id in zip(
    #             return_codes, message_or_unique_ids
    #         ):
    #             if return_code == ResultCode.FAILED:
    #                 self.logger.error(
    #                     "Command ID: %s | LoadDishCfg command "
    #                     + "failed with error: %s",
    #                     self.command_id,
    #                     message_or_unique_id,
    #                 )
    #                 return ResultCode.FAILED, message_or_unique_id
    #
    #     self.logger.info(
    #         "Command ID: %s | Successfully invoked LoadDishCfg command on "
    #         " %s",
    #         self.command_id,
    #         self.csp_mln_adapter.dev_name,
    #     )
    #     return self.wait_for_command_completion(
    #         device_length=len(self.command_subs_list)
    #     )

    # def _invoke_load_dish_cfg_on_csp_master_ln(
    #     self, dishid_vcc_map_params: str
    # ) -> Tuple[ResultCode, list]:
    #     """
    #     Invoke LoadDishCfg command on Csp Master with
    #     vcc_map_params argument
    #
    #     Args:
    #         dishid_vcc_map_params (str): vcc_map_params
    #             info containing vcc_dish mapping
    #
    #     Returns:
    #         Tuple(ResultCode, str): tuple containing
    #         ResultCode and message
    #
    #     """
    #     self.logger.debug(
    #         "Command ID: %s | Invoking LoadDishCfg command on: %s",
    #         self.command_id,
    #         self.csp_mln_adapter.dev_name,
    #     )
    #     self.component_manager.dev_names_for_load_dish_cfg.append(
    #         self.csp_mln_adapter.dev_name
    #     )
    #     return_codes, message_or_unique_ids = self.invoke_command(
    #         [self.csp_mln_adapter],
    #         "Error in calling LoadDishCfg command on Csp Master Leaf Node",
    #         "LoadDishCfg",
    #         json.dumps(dishid_vcc_map_params),
    #     )
    #     if return_codes[0] not in [
    #         ResultCode.OK,
    #         ResultCode.QUEUED,
    #         ResultCode.STARTED,
    #     ]:
    #         err = "Failed LoadDishCfg command on Csp Master Leaf Node"
    #         self.component_manager.dish_vcc_validation_status = {
    #             f"{self.csp_mln_adapter.dev_name}": err
    #         }
    #         self.component_manager.update_dish_vcc_flag(False)
    #     return return_codes, message_or_unique_ids

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

    def _set_k_numbers_to_dish(self, dish_parameters: dict) -> None:
        """
        Set K numbers to Dish by invoking setKValue command on dish ln
        Args:
            dish_parameters (dict): Dish paramters
                with dishid and k values
        Returns:
            None
        """
        dish_adapters = self.get_dish_adapters()
        runtime_context = self.command_runtime_context
        try:
            for dish_id, vcc_k_map in dish_parameters.items():
                # Get Dish Number from dish id to get dish adapter
                dish_adapter = [
                    dish_adapter
                    for dish_adapter in dish_adapters
                    if dish_adapter.dev_name.endswith(dish_id.lower())
                ]
                if dish_adapter:
                    dish_adapter = dish_adapter[0]
                    k_value = vcc_k_map.get("k")
                    self.logger.debug(
                        "Command ID: %s | Invoking SetKValue command on: %s",
                        self.context.command_id,
                        dish_adapter.dev_name,
                    )
                    dish_adapter.proxy.command_inout_asynch(
                        "SetKValue",
                        k_value,
                        self.async_cb(dish_adapter.dev_name),
                    )
                    # name = dish_adapter.dev_name + "async"
                    # self.context.command_device_ids.append(name)
                    # Append dish dev names to track on which dish
                    # SetKValue is invoked
                    runtime_context.append_dish_dev_names(
                        dish_adapter.dev_name
                    )
                else:
                    error_message = (
                        f"Adapter not found for dish leaf node {dish_id}"
                    )
                    runtime_context.update_kval_aggregator(
                        dish_id, error_message
                    )
                    self.logger.error(error_message)
        except Exception as e:
            self.logger.exception(
                "Exception occured in calling setKvalue command on %s, "
                + "Exception: %s",
                dish_id,
                str(e),
            )
            raise SetKValueError(
                f"Error in calling setKvalue command on dish adapter {e}"
            ) from e

    @retry(tries=3, delay=1)
    def fetch_dishid_vcc_map(self, dish_cfg_params: str) -> Tuple[dict, str]:
        """
        Fetch the DishId-VCC map JSON.

        Args:
            dish_cfg_params (str): Dish config parameters

        Returns:
            Tuple(dict, str): tuple of `DishId-VCC map JSON`
            and `error message` if any

        """
        dish_vcc_map_json, error_message = self.get_dishid_vcc_map_json(
            json.loads(dish_cfg_params)
        )
        if error_message:
            raise Exception(error_message)
        return dish_vcc_map_json, error_message

    # def check_and_validate_dish_vcc_data(
    #     self, dishid_vcc_map_params: str
    # ) -> Tuple[dict, str]:
    #     """This method downloads dish vcc json from telmodel
    #     and validates the data.
    #
    #     Args:
    #         dishid_vcc_map_params (str): JSON string containing parameters
    #             to fetch the dish VCC map.
    #
    #     Returns:
    #         Tuple[dict, str]: A tuple containing the dish VCC map JSON
    #             and an error message string (empty if no error).
    #     """
    #     try:
    #         (
    #             dishid_vcc_map_json,
    #             _,
    #         ) = self.fetch_dishid_vcc_map(dishid_vcc_map_params)
    #     except Exception as exp:
    #         return "", str(exp)
    #     self.logger.debug(
    #         "DishId Vcc Map Json: %s",
    #         json.dumps(dishid_vcc_map_json),
    #     )
    #     # Validate the data
    #     (
    #         is_valid_dish_cfg,
    #         message,
    #     ) = self.load_dish_config_json_validator(dishid_vcc_map_json)
    #
    #     if not is_valid_dish_cfg:
    #         return "", message
    #     return dishid_vcc_map_json, ""

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
