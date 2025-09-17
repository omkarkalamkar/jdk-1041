"""Command Claas For Setting Global Pointing Model on Dishes"""

import json
import threading
from typing import Callable, Optional, Tuple

from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_telmodel.data import TMData

from ska_tmc_centralnode.commands.central_node_command import SetDishGPM


# pylint:disable =abstract-method
class SetGlobalPointingModel(SetDishGPM):
    """
    A class for CentralNode's SetGlobalPointingModel command.
    This command forms GPM CAR URI and provide it to Dish Leaf Node
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
        self.gpm_files = None
        self.gpm_cfg = self.component_manager.event_manager_object
        self.dish_gpm_params: str = ""
        # self.dish_vcc_config_json: dict = {}

    def apply_gpm(
        self,
        dish_gpm_params: str,
        logger=None,
        task_callback: Callable = None,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:
        """
        :param logger: logger
        :param dish_gpm_params: GPM params
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
        self.component_manager.command_in_progress = "SetGlobalPointingModel"
        self.component_manager.command_result = ResultCode.STARTED
        self.component_manager.start_timer(
            self.timeout_id,
            self.component_manager.command_timeout,
            self.timeout_callback,
        )
        error_message = ""
        gpm_files = ""
        if "receptors" not in dish_gpm_params:
            (
                gpm_files,
                error_message,
            ) = self.get_gpm_files(dish_gpm_params)
            gpm_data = self.form_gpm_file_for_each_dish(
                self.gpm_files, self.dish_gpm_params
            )
        else:
            gpm_data = self.form_gpm_path_from_receptors(argin=dish_gpm_params)
        if error_message:
            # self.component_manager.gpm_status = {
            #     CENTRALNODE_MID: error_message
            # }
            self.logger.debug(
                "Command ID: %s",
                self.component_manager.command_id,
            )
            self.component_manager.reset_gpm_data()
            task_callback(
                status=TaskStatus.COMPLETED,
                result=(ResultCode.FAILED, error_message),
                exception=error_message,
            )
            return
        self.gpm_files = gpm_files
        self.dish_gpm_params = dish_gpm_params

        ret_code, message = self.do(gpm_data)
        self.logger.debug(
            "Command ID: %s | Message: %s ",
            self.component_manager.command_id,
            message,
        )
        if ret_code == ResultCode.FAILED:
            self.component_manager.reset_gpm_data()
            task_callback(
                status=TaskStatus.COMPLETED,
                result=(ResultCode.FAILED, message),
                exception=message,
            )
        else:
            self.start_tracker_thread(
                "get_set_gpm_version_resultcode",
                [ResultCode.OK],
                task_abort_event,
                timeout_id=self.timeout_id,
                timeout_callback=self.timeout_callback,
                command_id=self.component_manager.command_id,
                lrcr_callback=(
                    self.component_manager.long_running_result_callback
                ),
            )
        self.component_manager.set_gpm_version_command_id = (
            self.component_manager.command_id
        )

    def form_gpm_path_from_receptors(self, argin: dict):
        """"""
        gpm_data = {}
        default_params = (
            self.component_manager.get_default_gpm_version_params()
        )
        interface = default_params.get("interface", None)
        tm_data_sources = default_params.get("tm_data_sources", None)[0]
        tm_data_sources = (
            tm_data_sources
            + "?"
            + default_params.get("version", None)
            + "#tmdata"
        )
        receptors = json.loads(argin)["receptors"].items()
        for dish_id, bands in receptors:
            dish_id = dish_id.lower()
            for band in bands:
                file_name = f"gpm-{dish_id.lower()}-{band}.json"
                if dish_id not in gpm_data:
                    gpm_data[dish_id] = []
                tm_data_filepath = (
                    default_params.get("tm_data_filepath", None)
                    + "/"
                    + file_name
                )
                gpm_data[dish_id].append(
                    {
                        "interface": interface,
                        "tm_data_sources": tm_data_sources,
                        "tm_data_filepath": tm_data_filepath,
                    }
                )
        return gpm_data

    def form_gpm_file_for_each_dish(self, gpm_files, dish_gpm_params) -> dict:
        """Method to form gpm data"""
        gpm_data = {}
        try:
            tm_data_source = dish_gpm_params.get("tm_data_sources", None)
            tm_data_fpath = dish_gpm_params.get("tm_data_filepath", None)
            interface = dish_gpm_params.get("interface", None)
            version = dish_gpm_params.get("version", None)
            while not gpm_files:
                file_name = gpm_files.pop()
                dish_id = file_name.split("-")[1]
                tm_data_sources = tm_data_source + "?" + version + "#tmdata"
                tm_data_filepath = tm_data_fpath + file_name
                if dish_id not in gpm_data:
                    gpm_data[dish_id] = []
                gpm_data[dish_id].append(
                    {
                        "interface": interface,
                        "tm_data_sources": tm_data_sources,
                        "tm_data_filepath": tm_data_filepath,
                    }
                )
        except Exception as e:
            self.logger.exception("Exception %s occurred", e)
        return gpm_data

    def update_task_status(
        self, result: Tuple[ResultCode, str], exception: str = ""
    ) -> None:
        """
        Updates the task status for command

        Args:
            result: Result code of command
            exception (str): any message returned as a part of command

        """
        if not self.component_manager.gpm_aggregated_result:
            result = list(result)
            result[0] = ResultCode.FAILED
            result[1] = json.dumps(
                self.component_manager.dishln_gpm_data_created_during_command_execution
            )
            result = tuple(result)
            self.task_callback(
                result=result,
                status=TaskStatus.COMPLETED,
                exception="Command Failed",
            )
        else:
            result = list(result)
            result[1] = json.dumps(
                self.component_manager.dishln_gpm_data_created_during_command_execution
            )
            result = tuple(result)
            self.task_callback(result=result, status=TaskStatus.COMPLETED)
        self.logger.info(
            "Command ID: %s | Calling task callback for "
            + "SetGlobalPointingModel with Result: "
            + "%s and Message: %s",
            self.component_manager.command_id,
            result,
            exception,
        )
        self.component_manager.command_in_progress = ""
        if self.component_manager.command_mapping.get(
            self.component_manager.command_id
        ):
            self.component_manager.command_mapping.pop(
                self.component_manager.command_id
            )
        self.component_manager.reset_gpm_data()

    def get_gpm_files(self, initial_params: dict) -> Tuple[dict, str]:
        """
        Get GPM URI paths from initial params
        Args:
            initial_param (dict): this param containg tm
                data source uri and file path which is used
                for extracting vcc_map json file

        Returns:
            Tuple(dict, str): tuple having `dish_id with its GPM URI` and
            `Error message` if any

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
                tmdata = TMData(data_sources)
                gpm_path = tmdata[tm_data_filepath]
                gpm_files = list(gpm_path)
                return gpm_files, ""
            except Exception as exception:
                self.logger.exception(
                    "Command ID: %s |  Error in Loading GPM "
                    + "json file %s,",
                    self.component_manager.command_id,
                    exception,
                )
                return (
                    {},
                    f"Error in fetching GPM file {exception}",
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

        result_code, message = self.init_adapters()
        if result_code == ResultCode.FAILED:
            self.logger.error(
                "Command ID: %s | Failed to initialize adapters: %s",
                self.component_manager.command_id,
                message,
            )
            return result_code, message

        self._set_gpm_to_dish(argin)

        self.logger.info(
            "Command ID: %s | Successfully invoked SetGlobalPointingModel command on "
            " %s",
            self.component_manager.command_id,
            "mid-tmc/leaf-node-dish/ska001",
        )
        return ResultCode.OK, ""

    def _set_gpm_to_dish(self, gpm_data: dict) -> Tuple[ResultCode, str]:
        """
        Set GPM to Dish by invoking ApplyPointingModel
        command on dish dish leaf node.

        Args:
            gpm_data (dict): GPM data per dish

        Returns:
            Tuple(ResultCode, str): tuple containing
            ResultCode and message

        """
        return_codes = []
        message_or_unique_ids = []
        dishln_adapter = None
        try:
            for dish_id, bands in gpm_data.items():
                if self.component_manager.is_already_assigned(
                    dish_id.upper()
                ) or self.component_manager.is_already_assigned(
                    dish_id.lower()
                ):
                    error_message = "Dish is assigned to subarray"
                    self.add_data_to_gpm_dictionary_in_case_of_error(
                        dish_id, error_message
                    )
                    continue
                dishln_adapter = [
                    adapter
                    for adapter in self.dish_adapters
                    if dish_id in adapter.dev_name
                ]
                if dishln_adapter:
                    dishln_adapter = dishln_adapter[0]
                    self.logger.info(
                        "Command ID: %s | Invoking GPM command on: %s",
                        self.component_manager.command_id,
                        dishln_adapter,
                    )
                else:
                    error_message = "Dish is unreachable"
                    self.add_data_to_gpm_dictionary_in_case_of_error(
                        dish_id, error_message
                    )
                    self.logger.error(error_message)
                    continue
                for band in bands:
                    return_codes, message_or_unique_ids = self.send_command(
                        [dishln_adapter],
                        "Error in calling SetGlobalPointingModel command on Dish Leaf Node",
                        "ApplyPointingModel",
                        json.dumps(band),
                    )
                    if return_codes[0] == int(ResultCode.QUEUED):
                        with self.component_manager.dishln_gpm_lock:
                            self.component_manager.number_of_gpm_executed += 1
                    tm_data_filepath = band["tm_data_filepath"]
                    dishln_id = tm_data_filepath.split("/")[-1].split("-")[-2]
                    dishln_band = (
                        tm_data_filepath.split("/")[-1]
                        .split("-")[-1]
                        .split(".")[0]
                    )
                    if (
                        dishln_id
                        not in self.component_manager.dishln_gpm_data_created_during_command_execution
                    ):
                        self.component_manager.dishln_gpm_data_created_during_command_execution[
                            dishln_id
                        ] = {}
                    self.component_manager.dishln_gpm_data_created_during_command_execution[
                        dishln_id
                    ][
                        dishln_band
                    ] = None
                    self.logger.info(
                        ">>>>>> DICT :%s",
                        self.component_manager.dishln_gpm_data_created_during_command_execution,
                    )
            if not self.component_manager.number_of_gpm_executed:
                self.component_manager.aggregate_set_gpm_results()
                self.component_manager.gpm_version_aggregated_result = (
                    ResultCode.OK
                )
                self.component_manager.observable.notify_observers(
                    command_exception=True
                )
        except Exception as e:
            self.logger.exception(
                "Exception occured in Calling ApplyPointingModel command on %s, "
                + "Exception: %s",
                dishln_adapter.dev_name,
                str(e),
            )
            return [ResultCode.FAILED], [
                f"Error in Calling ApplyPointingModel command on dish adapter {e}"
            ]
        return return_codes, message_or_unique_ids

    def add_data_to_gpm_dictionary_in_case_of_error(
        self, dish_id, error_message
    ):
        if (
            dish_id
            not in self.component_manager.dishln_gpm_data_created_during_command_execution
        ):
            self.component_manager.dishln_gpm_data_created_during_command_execution[
                dish_id
            ] = {}
        self.component_manager.dishln_gpm_data_created_during_command_execution[
            dish_id
        ] = [
            ResultCode.FAILED,
            error_message,
        ]
