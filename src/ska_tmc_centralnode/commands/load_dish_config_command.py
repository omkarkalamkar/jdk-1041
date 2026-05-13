"""Commad class for Load_dish_config_command"""

import json
import time
from typing import Tuple

from retry import retry
from ska_control_model import TaskStatus
from ska_tango_base.commands import ResultCode
from ska_telmodel.data import TMData

from ska_tmc_centralnode.commands.central_node_command import (
    LoadDishCfgCommand,
)
from ska_tmc_centralnode.model.enum import DishConfigStatus
from ska_tmc_centralnode.utils.config_json_validator import DishConfigValidator
from ska_tmc_centralnode.utils.constants import CENTRALNODE_MID


# pylint:disable =abstract-method
class LoadDishCfg(LoadDishCfgCommand):
    """
    A class for CentralNode's LoadDishConfig command.
    Load DishId-VCC map from CAR URI and provide it to Csp Master Leaf Node
    After Validation
    """

    # pylint:disable=keyword-arg-before-vararg

    def __init__(
        self,
        component_manager,
        adapter_factory=None,
        timeout_subarrays=3,
        step_sleep=0.1,
        logger=None,
        *args,
        **kwargs,
    ):
        super().__init__(
            component_manager, adapter_factory, logger=logger, *args, **kwargs
        )
        self._timeout_subarrays = timeout_subarrays
        self._step_sleep = step_sleep
        self.dish_cfg = self.component_manager.event_manager_object
        self.dish_cfg_params: str = ""
        self.dish_vcc_config_json: dict = {}

    def set_command_id(self, command_name: str) -> None:
        """Sets the command id for error propagation.

        :param command_name: name of the command.
        :type command_name: str
        """
        self.command_id = f"{time.time()}-{command_name}"
        self.logger.info(
            "Setting command id as %s for command: %s",
            self.command_id,
            command_name,
        )
        self.component_manager.command_id = self.command_id

    def load_dish_cfg(
        self,
        argin: str,
        task_callback,
        task_abort_event,
    ) -> Tuple[ResultCode, str]:
        """
        Load Dish Configuration command.
        Validates dish-vcc data, executes lower-level command.

        Args:
            argin (str): Input argument for the command.

        Returns:
            Tuple(ResultCode, str): Result code and message.

        """
        self.component_manager.command_in_progress = "LoadDishCfg"
        self.task_callback = task_callback
        self.task_abort_event = task_abort_event
        self.component_manager.abort_event = self.task_abort_event
        self.task_callback(status=TaskStatus.IN_PROGRESS)

        # Set Dish-specific command status
        self.component_manager.dish_vcc_command_status = (
            DishConfigStatus.IN_PROGRESS
        )

        # Validate
        (
            dish_vcc_map_json,
            error_message,
        ) = self.check_and_validate_dish_vcc_data(argin)
        if error_message:
            self.component_manager.dish_vcc_validation_status = {
                CENTRALNODE_MID: error_message
            }
            self.update_task_status(
                result=(ResultCode.FAILED, error_message),
                exception=error_message,
            )
            return ResultCode.FAILED, error_message

        # Save validated config
        self.dish_vcc_config_json = dish_vcc_map_json
        self.dish_cfg_params = argin

        # Execute device-level command
        self.component_manager.load_dish_cfg_command_id = self.command_id
        result, message = self.do(argin)
        self.update_task_status(result=(result, message), exception=message)
        return result, message

    def update_task_status(
        self, result: Tuple[ResultCode, str], exception: str = ""
    ) -> None:
        """
        Updates the task status for command

        Args:
            result: Result code of command
            exception (str): any message returned as a part of command

        """
        self.logger.debug(
            "Task callback invoked | command=LoadDishCfg id=%s result=%s "
            "message=%s",
            self.command_id,
            str(result[0]),
            exception,
        )
        self.component_manager.dish_vcc_command_status = (
            DishConfigStatus.COMPLETED
        )
        if result[0] == ResultCode.FAILED:
            self.component_manager.update_dish_vcc_flag(False)
            self.task_callback(
                result=result,
                status=TaskStatus.COMPLETED,
                exception=exception,
            )
        else:
            self.update_memorized_attribute()
            self.component_manager.update_dish_vcc_flag(True)
            self.task_callback(result=result, status=TaskStatus.COMPLETED)
        self.component_manager.command_in_progress = ""
        if self.component_manager.command_mapping.get(self.command_id):
            self.component_manager.command_mapping.pop(self.command_id)
        self.component_manager.reset_load_dish_cfg_data()

    def update_memorized_attribute(self) -> None:
        """
        Update memorized attribute so after restart this
        attribute used to get dish map vcc version set before
        restart
        """
        self.csp_mln_adapter.memorizedDishVccMap = self.dish_cfg_params

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
            self.command_id,
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
                    self.command_id,
                    exception,
                )
                return (
                    {},
                    f"Error in Loading Dish VCC map json file {exception}",
                )
        return {}, "tm_data_sources and tm_data_filepath not provided in json"

    # pylint:disable=signature-differs
    def do(self, argin: str) -> Tuple[ResultCode, str]:
        """
        This command performs the following steps:\n
        1. Loads the content of the DishId-VCC mapping file from CAR URI.\n
        2. Validates the JSON.\n
        3. Invokes a command on the CSP master leaf node.\n
        4. Invokes the SetKValue command on the Dish Leaf Node for each dish ID
        provided in the DishId-VCC map.\n

        Args:
            argin (str): DishId-VCC map parameters in JSON string format.

        Returns:
            Tuple(ResultCode, str): Result code and message

        """
        self.set_command_id(self.__class__.__name__)
        self.logger.debug(
            "Command %s: Executing LoadDishCfg command",
            self.command_id,
        )

        result_code, message = self.init_adapters()
        if result_code == ResultCode.FAILED:
            self.logger.error(
                "Adapter initialization failed | command_id=%s error=%s",
                self.command_id,
                message,
            )
            return result_code, message

        dishid_vcc_map_params = json.loads(argin)
        self.logger.debug(
            "DishId-VCC map parameters | command_id=%s params=%s",
            self.command_id,
            json.dumps(dishid_vcc_map_params),
        )

        dish_parameters = self.dish_vcc_config_json.get("dish_parameters")

        for return_codes, message_or_unique_ids in [
            self._invoke_load_dish_cfg_on_csp_master_ln(dishid_vcc_map_params),
            self._set_k_numbers_to_dish(dish_parameters),
        ]:
            for return_code, message_or_unique_id in zip(
                return_codes, message_or_unique_ids
            ):
                if return_code == ResultCode.FAILED:
                    self.logger.error(
                        "Command ID: %s | LoadDishCfg command "
                        + "failed with error: %s",
                        self.command_id,
                        message_or_unique_id,
                    )
                    return ResultCode.FAILED, message_or_unique_id

        self.logger.info(
            "Command ID: %s | Successfully invoked LoadDishCfg command on "
            " %s",
            self.command_id,
            self.csp_mln_adapter.dev_name,
        )
        return self.wait_for_command_completion(len(self.command_subs_list))

    def _invoke_load_dish_cfg_on_csp_master_ln(
        self, dishid_vcc_map_params: str
    ) -> Tuple[ResultCode, list]:
        """
        Invoke LoadDishCfg command on Csp Master with
        vcc_map_params argument

        Args:
            dishid_vcc_map_params (str): vcc_map_params
                info containing vcc_dish mapping

        Returns:
            Tuple(ResultCode, str): tuple containing
            ResultCode and message

        """
        self.logger.info(
            "Command ID: %s | Invoking LoadDishCfg command on: %s",
            self.command_id,
            self.csp_mln_adapter.dev_name,
        )
        self.component_manager.dev_names_for_load_dish_cfg.append(
            self.csp_mln_adapter.dev_name
        )
        return_codes, message_or_unique_ids = self.invoke_command(
            [self.csp_mln_adapter],
            "Error in calling LoadDishCfg command on Csp Master Leaf Node",
            "LoadDishCfg",
            json.dumps(dishid_vcc_map_params),
        )
        return return_codes, message_or_unique_ids

    def _set_k_numbers_to_dish(
        self, dish_parameters: dict
    ) -> Tuple[ResultCode, str]:
        """
        Set K numbers to Dish by invoking setKValue command on dish ln

        Args:
            dish_parameters (dict): Dish paramters
                with dishid and k values

        Returns:
            Tuple(ResultCode, str): tuple containing
            ResultCode and message

        """
        return_codes = []
        message_or_unique_ids = []
        try:
            for dish_id, vcc_k_map in dish_parameters.items():
                # Get Dish Number from dish id to get dish adapter
                dish_adapter = [
                    dish_adapter
                    for dish_adapter in self.dish_adapters
                    if dish_adapter.dev_name.endswith(dish_id)
                ]
                if dish_adapter:
                    dish_adapter = dish_adapter[0]
                    k_value = vcc_k_map.get("k")
                    self.logger.debug(
                        "Command ID: %s | Invoking SetKValue command on: %s",
                        self.command_id,
                        dish_adapter.dev_name,
                    )
                    dish_adapter.proxy.command_inout_asynch(
                        "SetKValue",
                        k_value,
                        self.async_cb(dish_adapter.dev_name),
                    )
                    name = dish_adapter.dev_name + "async"
                    self.command_subs_list.append(name)
                    # Append dish dev names to track on which dish
                    # SetKValue is invoked
                    self.component_manager.dev_names_for_load_dish_cfg.append(
                        dish_adapter.dev_name
                    )
                else:
                    error_message = (
                        f"Dish adapter not found for dish id {dish_id}"
                    )
                    self.logger.error(error_message)
        except Exception as e:
            self.logger.exception(
                "Exception occured in calling setKvalue command on %s, "
                + "Exception: %s",
                dish_adapter.dev_name,
                str(e),
            )
            return [ResultCode.FAILED], [
                f"Error in calling setKvalue command on dish adapter {e}"
            ]

        return return_codes, message_or_unique_ids

    def load_dish_config_json_validator(self, argin) -> tuple[bool, str]:
        """
        Method to validate the JSON for LoadDishConfig Command

        Args:
            argin: Input argument for DishConfigValidator

        Returns:
            Tuple(bool, str): Tuple of `boolean`
            representing `valid dish config`
            and `string` representing `message`

        """
        config_json_validator = DishConfigValidator(
            argin,
            self.component_manager.k_value_valid_range_lower_limit,
            self.component_manager.k_value_valid_range_upper_limit,
        )
        is_valid_dish_cfg, message = config_json_validator.is_json_valid()
        return is_valid_dish_cfg, message

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

    def check_and_validate_dish_vcc_data(
        self, dishid_vcc_map_params: str
    ) -> Tuple[dict, str]:
        """This method downloads dish vcc json from telmodel
        and validates the data.

        Args:
            dishid_vcc_map_params (str): JSON string containing parameters
                to fetch the dish VCC map.

        Returns:
            Tuple[dict, str]: A tuple containing the dish VCC map JSON
                and an error message string (empty if no error).
        """
        try:
            (
                dishid_vcc_map_json,
                _,
            ) = self.fetch_dishid_vcc_map(dishid_vcc_map_params)
        except Exception as exp:
            return "", str(exp)
        self.logger.debug(
            "DishId Vcc Map Json: %s",
            json.dumps(dishid_vcc_map_json),
        )
        # Validate the data
        (
            is_valid_dish_cfg,
            message,
        ) = self.load_dish_config_json_validator(dishid_vcc_map_json)

        if not is_valid_dish_cfg:
            return "", message
        return dishid_vcc_map_json, ""

    def async_cb(self, device_name: str):
        """Invoke LRC callback.
        Provide this callback whenever command is invoked using invoke_lrc api
        Args:
            device_name: Name Of Device
        Returns:
            callback: function object to provided to invoke_lrc
        """

        def callback(event_data):
            if event_data:
                value = event_data.argout
                result = [value[0][0], value[1][0]]
                with self.component_manager.command_completion_cond:
                    self.command_results[device_name] = result
                    cond = self.component_manager.command_completion_cond
                    with cond:
                        cond.notify_all()

        return callback
