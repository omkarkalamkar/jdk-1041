"""Commad class for Load_dish_config_command"""
import json
import threading
from typing import Callable, Optional, Tuple

from retry import retry
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
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
        self.dish_cfg = self.component_manager.event_receiver_object
        self.dish_cfg_params: str = ""

    def load_dish_cfg(
        self,
        dish_cfg_params: str,
        logger=None,
        task_callback: Callable = None,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:
        """:param logger: logger
        :param dish_cfg_params: dishid vcc map params
        :type logger: logging.Logger
        :param task_callback: Update task state, defaults to None
        :type task_callback: Callable, optional
        :param task_abort_event: Check for abort, defaults to None
        :type task_abort_event: Event, optional
        """
        # Indicate that the task has started
        self.task_callback = task_callback
        self.set_command_id(__class__.__name__)
        self.task_callback(status=TaskStatus.IN_PROGRESS)
        self.component_manager.command_in_progress = "LoadDishCfg"
        self.component_manager.command_result = ResultCode.STARTED
        self.component_manager.dish_vcc_command_status = (
            DishConfigStatus.IN_PROGRESS
        )
        self.component_manager.start_timer(
            self.timeout_id,
            self.component_manager.command_timeout,
            self.timeout_callback,
        )
        if self.component_manager.dish_vcc_data_download_error is True:
            (
                dishid_vcc_map_json,
                error_message,
            ) = self.fetch_dishid_vcc_map(dish_cfg_params)
            if error_message:
                self.component_manager.dish_vcc_validation_status = {
                    CENTRALNODE_MID: error_message
                }
                self.logger.debug(
                    "Command ID | %s " + "Number of retries exhausted",
                    self.component_manager.command_id,
                )
                self.component_manager.reset_load_dish_cfg_data()
                task_callback(
                    status=TaskStatus.COMPLETED,
                    result=(ResultCode.FAILED, error_message),
                    exception=error_message,
                )
                self.component_manager.dish_vcc_data_download_error = False
                return

            self.logger.info(
                "Command ID: %s | DishId Vcc Map Json %s",
                json.dumps(
                    dishid_vcc_map_json
                    if isinstance(dishid_vcc_map_json, dict)
                    else json.loads(dishid_vcc_map_json),
                    indent=4,
                ),
                self.component_manager.command_id,
            )
            is_valid_dish_cfg, message = self.load_dish_config_json_validator(
                dishid_vcc_map_json
            )
            if not is_valid_dish_cfg:
                self.component_manager.dish_vcc_validation_status = {
                    CENTRALNODE_MID: message
                }
                self.component_manager.reset_load_dish_cfg_data()
                task_callback(
                    status=TaskStatus.COMPLETED,
                    result=(ResultCode.FAILED, message),
                    exception=message,
                )
                return

        ret_code, message = self.do(dish_cfg_params)
        self.dish_cfg_params = dish_cfg_params
        self.logger.info(
            "Command ID: %s | %s ", self.component_manager.command_id, message
        )
        if ret_code == ResultCode.FAILED:
            self.component_manager.reset_load_dish_cfg_data()
            task_callback(
                status=TaskStatus.COMPLETED,
                result=(ResultCode.FAILED, message),
                exception=message,
            )
        else:
            self.start_tracker_thread(
                "get_load_disg_cfg_resultcode",
                [ResultCode.OK],
                task_abort_event,
                timeout_id=self.timeout_id,
                timeout_callback=self.timeout_callback,
                command_id=self.component_manager.command_id,
                lrcr_callback=(
                    self.component_manager.long_running_result_callback
                ),
            )
        self.component_manager.load_dish_cfg_command_id = (
            self.component_manager.command_id
        )

    def update_task_status(
        self, result: Tuple[ResultCode, str], exception: str = ""
    ):
        """Updates the task status for command
        :param result: Result code of command
        :type: ResultCode enum
        :param message: any message returned as a part of command
        :type message: str
        """
        self.logger.debug(
            "Command ID: %s | Calling task callback for "
            + "LoadDishCfg with result"
            + "%s and message %s",
            self.component_manager.command_id,
            result,
            exception,
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
        if self.component_manager.command_mapping.get(
            self.component_manager.command_id
        ):
            self.component_manager.command_mapping.pop(
                self.component_manager.command_id
            )
        self.component_manager.reset_load_dish_cfg_data()

    def update_memorized_attribute(self) -> None:
        """Update memorized attribute so after restart this
        attribute used to get dish map vcc version set before
        restart
        """
        self.csp_mln_adapter.memorizedDishVccMap = self.dish_cfg_params

    def get_dishid_vcc_map_json(
        self, initial_params: dict
    ) -> Tuple[dict, str]:
        """Get DishId-VCC map json from initial params
        :param initial_param: this param containg tm data source uri
        and file path which is used for extracting vcc_map json file
        """
        data_sources = initial_params.get("tm_data_sources", None)
        tm_data_filepath = initial_params.get("tm_data_filepath", None)
        self.logger.debug(
            "Command ID: %s | The initial params are : %s",
            self.component_manager.command_id,
            json.dumps(initial_params, indent=2),
        )
        if data_sources and tm_data_filepath:
            try:
                data = TMData(data_sources)
                return data[tm_data_filepath].get_dict(), ""
            except Exception as exception:
                self.logger.exception(
                    "Command ID: %s |  Error in Loading Dish VCC map "
                    + "json file %s, retrying",
                    self.component_manager.command_id,
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
        This command performs the following steps:
        1. Loads the content of the DishId-VCC mapping file from CAR URI.
        2. Validates the JSON.
        3. Invokes a command on the CSP master leaf node.
        4. Invokes the SetKValue command on the Dish Leaf Node for each dish ID
        provided in the DishId-VCC map.

        :param argin: DishId-VCC map parameters in JSON string format.
        :type argin: str
        :return: Result code and message
        :rtype: Tuple[ResultCode, str]
        """

        result_code, message = self.init_adapters()
        if result_code == ResultCode.FAILED:
            self.logger.error(
                "Command ID: %s | Failed to initialize adapters: %s",
                self.component_manager.command_id,
                message,
            )
            return result_code, message

        dishid_vcc_map_params = json.loads(argin)
        self.logger.info(
            "Command ID: %s | DishId-VCC map parameters: %s",
            self.component_manager.command_id,
            json.dumps(dishid_vcc_map_params, indent=4),
        )

        dishid_vcc_map_json, _ = self.get_dishid_vcc_map_json(
            dishid_vcc_map_params
        )

        dish_parameters = dishid_vcc_map_json.get("dish_parameters")

        for return_codes, message_or_unique_ids in [
            self._invoke_load_dish_cfg_on_csp_master_ln(dishid_vcc_map_params),
            self._set_k_numbers_to_dish(dish_parameters),
        ]:
            for return_code, message_or_unique_id in zip(
                return_codes, message_or_unique_ids
            ):
                if return_code == ResultCode.FAILED:
                    self.logger.error(
                        "Command ID: %s | Command LoadDishCfg "
                        + "failed with error: %s",
                        self.component_manager.command_id,
                        message_or_unique_id,
                    )
                    return ResultCode.FAILED, message_or_unique_id

        self.logger.info(
            "Command ID: %s | Successfully invoked LoadDishCfg command on "
            " %s",
            self.component_manager.command_id,
            self.csp_mln_adapter.dev_name,
        )
        return ResultCode.OK, ""

    def _invoke_load_dish_cfg_on_csp_master_ln(
        self, dishid_vcc_map_params: str
    ) -> Tuple[ResultCode, list]:
        """Invoke LoadDishCfg command on Csp Master with
         vcc_map_params argument
        :param dishid_vcc_map_params:
        vcc_map_params info containing vcc_dish mapping
        """
        self.logger.info(
            "Command ID: %s | Invoking LoadDishCfg command on: %s",
            self.component_manager.command_id,
            self.csp_mln_adapter.dev_name,
        )
        self.component_manager.dev_names_for_load_dish_cfg.append(
            self.csp_mln_adapter.dev_name
        )
        return_codes, message_or_unique_ids = self.send_command(
            [self.csp_mln_adapter],
            "Error in calling LoadDishCfg command on Csp Master Leaf Node",
            "LoadDishCfg",
            json.dumps(dishid_vcc_map_params),
        )
        return return_codes, message_or_unique_ids

    def _set_k_numbers_to_dish(
        self, dish_parameters: dict
    ) -> Tuple[ResultCode, str]:
        """Set K numbers to Dish by invoking setKValue command on dish ln
        :params dish_parametes: Dish paramters with dishid and k values
        """
        return_codes = []
        message_or_unique_ids = []
        try:
            for dish_id, vcc_k_map in dish_parameters.items():
                # Get Dish Number from dish id to get dish adapter
                dish_number = dish_id[-3:]
                dish_adapter = [
                    dish_adapter
                    for dish_adapter in self.dish_adapters
                    if dish_adapter.dev_name[-3:] == dish_number
                ]
                if dish_adapter:
                    dish_adapter = dish_adapter[0]
                    k_value = vcc_k_map.get("k")
                    self.logger.info(
                        "Command ID: %s | " + "Invoking SetKValue on %s",
                        self.component_manager.command_id,
                        dish_adapter.dev_name,
                    )
                    dish_adapter.proxy.command_inout_asynch(
                        "SetKValue",
                        k_value,
                        self.dish_cfg.handle_load_dish_cfg_result_callback,
                    )
                    # Append dish dev names to track on which dish
                    # SetKValue is invoked
                    self.component_manager.dev_names_for_load_dish_cfg.append(
                        dish_adapter.dev_name
                    )
                else:
                    error_message = (
                        f"Dish adapter not found for dish id {dish_id}"
                    )
                    self.logger.info(error_message)
        except Exception as e:
            self.logger.exception(
                "Error in Calling setKvalue command on %s : %s",
                dish_adapter.dev_name,
                e,
            )
            return [ResultCode.FAILED], [
                "Error in Calling setKvalue command on %s : %s",
                dish_adapter.dev_name,
                e,
            ]

        return return_codes, message_or_unique_ids

    def load_dish_config_json_validator(self, argin):
        """
        Method to validate the JSON for LoadDishConfig Command
        """
        config_json_validator = DishConfigValidator(
            argin,
            self.component_manager.k_value_valid_range_lower_limit,
            self.component_manager.k_value_valid_range_upper_limit,
        )
        is_valid_dish_cfg, message = config_json_validator.is_json_valid()
        return is_valid_dish_cfg, message

    @retry(tries=3, delay=1)
    def fetch_dishid_vcc_map(self, dish_cfg_params):
        """Fetch the DishId-VCC map JSON."""
        return self.get_dishid_vcc_map_json(json.loads(dish_cfg_params))
