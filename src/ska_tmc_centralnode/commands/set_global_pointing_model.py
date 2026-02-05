"""Command Claas For Setting Global Pointing Model on Dishes"""

import json
import threading
from functools import partial
from typing import Callable, Optional, Tuple

from ska_control_model import TaskStatus
from ska_tango_base.commands import ResultCode
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
        self.dish_gpm_params: str = ""

    def apply_gpm(
        self,
        dish_gpm_params: str,
        logger=None,
        task_callback: Callable = None,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:
        """
        Applies the Global Pointing Model (GPM) to dishes
        using the provided parameters. Parses the input
        JSON parameters, prepares GPM data per dish,
        and invokes the command to set the GPM on dish leaf nodes.

        Args:
            dish_gpm_params (str): JSON string with GPM parameters.
            logger (optional): Logger instance.
            task_callback (Callable, optional): Callback to update task status.
            task_abort_event (threading.Event, optional): task abort event.

        Returns:
            None
        """
        # Indicate that the task has started
        self.task_callback = task_callback
        self.set_command_id(__class__.__name__)
        self.task_callback(status=TaskStatus.IN_PROGRESS)
        self.component_manager.command_in_progress = "SetGlobalPointingModel"
        self.component_manager.command_result = ResultCode.STARTED
        self.dish_gpm_params = json.loads(dish_gpm_params)
        error_message = ""
        if "receptors" not in self.dish_gpm_params:
            gpm_files = self.get_gpm_files(self.dish_gpm_params)
            if not gpm_files:
                error_message = "No GPM files found on set GPM parameters."
                self.process_update_task_for_command_failure(
                    self.task_callback, error_message
                )
                self.component_manager.reset_gpm_data()
                self.logger.debug("Error message: %s", error_message)
                return ResultCode.REJECTED, error_message
            gpm_data = self.form_gpm_file_for_each_dish(
                gpm_files, self.dish_gpm_params
            )
        else:
            gpm_data = self.form_gpm_path_from_receptors(self.dish_gpm_params)

        result, message = self.do(gpm_data)
        self.call_update_task_status(result, message)
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
        if result[0] == ResultCode.FAILED:
            error_message = "SetGPM failed on: "
            self.process_update_task_for_command_failure(
                self.task_callback, error_message
            )
            self.logger.debug("Error message: %s", error_message)
        else:
            result = list(result)
            result[1] = self.component_manager.dishln_gpm_cmd_exe_data
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
        self.component_manager.reset_gpm_data()

    def process_update_task_for_command_failure(
        self, task_callback, error_message: str
    ) -> None:
        """Method to update the task callback and GPM status
        with the failure data

        Args:
            task_callback: Update task state with the failure data
        """

        if self.component_manager.dishln_gpm_cmd_exe_data:
            for (
                dish_id,
                result,
            ) in self.component_manager.dishln_gpm_cmd_exe_data.items():
                if isinstance(result, str):
                    if (
                        "Dish is assigned to subarray" not in result
                        and "Dish is unreachable" not in result
                    ):
                        self.component_manager.global_pointing_model_status[
                            dish_id
                        ] = result

            error_message = error_message + str(
                self.filter_failed_dish_data(
                    self.component_manager.dishln_gpm_cmd_exe_data
                )
            )
        task_callback(
            status=TaskStatus.COMPLETED,
            result=(ResultCode.FAILED, error_message),
            exception=error_message,
        )

    def filter_failed_dish_data(self, data: dict) -> dict:
        """Filter Failed Dish Data
        Args:
            data(dict): Dish Data
        Returns:
            dish dict
        """
        filtered = {}
        for dish, content in data.items():
            if isinstance(content, dict):
                bands = {
                    band: values
                    for band, values in content.items()
                    if values and values != 0
                }
                if bands:
                    filtered[dish] = bands
            else:
                filtered[dish] = content
        return filtered

    def form_gpm_path_from_receptors(self, argin: dict) -> dict:
        """This method forms the inputs for ApplyPointingModel command

        Args:
           argin: Dictionary which contains manual command input
           from operator.
        """
        gpm_data = {}
        default_params = (
            self.component_manager.get_default_gpm_version_params()
        )
        interface = default_params.get("interface", None)
        tm_data_sources = default_params.get("tm_data_sources", None)[0]
        tm_data_sources = (
            tm_data_sources + "?" + argin.get("version", None) + "#tmdata"
        )
        receptors = argin["receptors"].items()

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

    def form_gpm_file_for_each_dish(
        self, gpm_files: list, dish_gpm_params: dict
    ) -> dict:
        """Method to form gpm data from gpm files found on GPM
        data repository.

        Args:
            gpm_files: GPM files found on data repository.
            dish_gpm_params: Default parameters set for GPM on initialization.
        """
        gpm_data = {}
        try:
            tm_data_source = dish_gpm_params.get("tm_data_sources", None)[0]
            tm_data_fpath = dish_gpm_params.get("tm_data_filepath", None)
            interface = dish_gpm_params.get("interface", None)
            version = dish_gpm_params.get("version", None)
            self.logger.info(
                "GPM Files found on data repository: %s", gpm_files
            )
            file_names = []
            while self.component_manager.gpm_unknown_dishes:
                dish_id = self.component_manager.gpm_unknown_dishes.pop()
                file_names = [
                    f for f in gpm_files if dish_id.lower() in f.lower()
                ]
                if not file_names:
                    self.logger.info("GPM file not found for dish %s", dish_id)
                    error_message = (
                        "No GPM files were found for any of"
                        + " the bands in the provided paths"
                    )
                    self.add_data_to_gpm_dictionary_in_case_of_error(
                        dish_id, error_message
                    )
                for file_name in file_names:
                    tm_data_sources = (
                        tm_data_source + "?" + version + "#tmdata"
                    )
                    tm_data_filepath = tm_data_fpath + "/" + file_name
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
            self.logger.exception("Exception %s occurred %s", e)
        return gpm_data

    def get_gpm_files(self, initial_params: dict) -> list:
        """
        Get GPM files from initial params

        Args:
            initial_param (dict): this param containg tm
                data source uri and file path which is used
                to get GPM files.

        Returns:
            list: containing GPM file names found on data repo.
        """

        gpm_files = []
        data_sources = initial_params.get("tm_data_sources", None)[0]
        tm_data_filepath = initial_params.get("tm_data_filepath", None)
        data_sources = (
            data_sources
            + "?"
            + initial_params.get("version", None)
            + "#tmdata"
        )
        self.logger.info(
            "Command ID: %s| The initial params are :  %s",
            self.component_manager.command_id,
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
                    self.component_manager.command_id,
                    exception,
                )
                return (
                    {},
                    f"Error in fetching GPM file {exception}",
                )
        return {}, "tm_data_sources and tm_data_filepath not provided in json"

    # pylint:disable=signature-differs
    def do(self, argin: dict) -> Tuple[ResultCode, str]:
        """
        This command performs invokes the ApplyPointingModel
        command on the dish_id's specified in argin which is a
        dictionary

        Args:
            argin (dict): gpm_data ready for execution.

        Returns:
            Tuple(ResultCode, str): Result code and message

        """
        if not argin:
            err_message = "Set GPM Command failed, argin is empty"
            self.logger.error(err_message)
            return [ResultCode.FAILED], [err_message]

        result_code, message = self.init_adapters()
        if result_code == ResultCode.FAILED:
            self.logger.error(
                "Command ID: %s | Failed to initialize adapters: %s",
                self.component_manager.command_id,
                message,
            )
            return result_code, message

        result_code, message = self._set_gpm_to_dish(argin)
        if result_code[0] not in [ResultCode.OK, ResultCode.QUEUED]:
            return (result_code, message)
        self.logger.info(
            "Command ID: %s | "
            "Successfully invoked SetGlobalPointingModel command on "
            " %s",
            self.component_manager.command_id,
            self.component_manager.dishln_gpm_cmd_exe_data.keys(),
        )
        return self.wait_for_command_completion(len(self.command_subs_list))

    def _set_gpm_to_dish(self, gpm_data: dict) -> Tuple[ResultCode, str]:
        """
        Set GPM to Dish by invoking ApplyPointingModel
        command on dish leaf node.

        Args:
            gpm_data (dict): GPM data per dish

        Returns:
            Tuple(ResultCode, str): tuple containing
            ResultCode and message

        """

        return_codes = [ResultCode.UNKNOWN]
        message_or_unique_ids = []
        dishln_adapter = None
        self.logger.info("GPM data for command execution:%s", gpm_data)
        try:
            for dish_id, bands in gpm_data.items():
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
                    return_codes[0] = ResultCode.FAILED
                    message_or_unique_ids.append(
                        f"Error: {dish_id} :{error_message}"
                    )
                    continue
                if self.component_manager.is_already_assigned(
                    dish_id.upper()
                ) or self.component_manager.is_already_assigned(
                    dish_id.lower()
                ):
                    error_message = "Dish is assigned to subarray"
                    self.add_data_to_gpm_dictionary_in_case_of_error(
                        dish_id, error_message
                    )
                    return_codes[0] = ResultCode.FAILED
                    message_or_unique_ids.append(
                        f"Error: {dish_id}: {error_message}"
                    )
                    self.logger.error(error_message)
                    continue
                for band in bands:
                    tm_data_filepath = band["tm_data_filepath"]
                    dishln_id = tm_data_filepath.split("/")[-1].split("-")[-2]
                    dishln_band = (
                        tm_data_filepath.split("/")[-1]
                        .split("-")[-1]
                        .split(".")[0]
                    )
                    callback = partial(
                        self.update_set_gpm_results, band_value=dishln_band
                    )
                    return_codes, message_or_unique_ids = self.invoke_command(
                        [dishln_adapter],
                        "Error in calling SetGlobalPointingModel"
                        "command on Dish Leaf Node",
                        "ApplyPointingModel",
                        json.dumps(band),
                        callback=callback,
                    )
                    if return_codes[0] == int(ResultCode.OK):
                        with self.component_manager.dishln_gpm_lock:
                            self.component_manager.number_of_gpm_executed += 1

                    if (
                        dishln_id
                        not in self.component_manager.dishln_gpm_cmd_exe_data
                    ):
                        self.component_manager.dishln_gpm_cmd_exe_data[
                            dishln_id
                        ] = {}
                    self.component_manager.dishln_gpm_cmd_exe_data[dishln_id][
                        dishln_band
                    ] = None
                self.logger.info(
                    "Finished executing APM on DLN."
                    "GPM data dictionary : %s",
                    self.component_manager.dishln_gpm_cmd_exe_data,
                )
            if not self.component_manager.number_of_gpm_executed:
                self.component_manager.aggregate_set_gpm_results()
                self.component_manager.gpm_version_aggregated_result = (
                    ResultCode.OK
                )
        except Exception as e:
            self.logger.exception(
                "Exception occured in Calling ApplyPointingModel, "
                + "Exception: %s",
                str(e),
            )
            return [ResultCode.FAILED], [
                "Error in Calling ApplyPointingModel"
                f" command on dish adapter {e}"
            ]

        if self.component_manager.number_of_gpm_executed:
            return [ResultCode.OK], [""]

        return return_codes, message_or_unique_ids

    def add_data_to_gpm_dictionary_in_case_of_error(
        self, dish_id: str, error_message: str
    ):
        """
        Update the GPM data with aggregated error for given
        dish_id

        Args:
            dish_id (str):
                Dish leaf node id.
            error_message (str):
                Error message.

        """
        if dish_id not in self.component_manager.dishln_gpm_cmd_exe_data:
            self.component_manager.dishln_gpm_cmd_exe_data[dish_id] = {}
        self.component_manager.dishln_gpm_cmd_exe_data[dish_id] = (
            "ERROR: " + error_message
        )

    def _set_band_command_mapping(self, command_id, band) -> None:
        """Set Band Command Mapping and Band
        Args:
            command_id: Command Id for the dish command
        """
        command_id_band_dict = {command_id: band}
        if (
            self.component_manager.command_id
            not in self.component_manager.command_mapping
        ):
            self.component_manager.command_mapping[
                self.component_manager.command_id
            ] = [command_id_band_dict]
        else:
            self.component_manager.command_mapping[
                self.component_manager.command_id
            ].append(command_id_band_dict)

    def update_set_gpm_results(self, dev_name: str, band_value: str) -> None:
        """
        This method is used to update the result returned
        from Dish leaf nodes as part of SetGlobalPointingModel
        command.
        If all events are received from all device then aggregate
        the result
        Value contains (unique_id, ResultCode)
        Args:
            dev_name (str): Name of the device who's event has been
            captured in this method
            value (tuple): longRunningCommandResult attribute event.
        """

        def callback(result=None, **kwargs):
            self.logger.info(
                "GPM longRunningCommandResult event for device: "
                "%s, with value: %s",
                dev_name,
                str(result),
            )
            with self.component_manager.dishln_gpm_lock:
                dishln_id = dev_name.split("/")[-1]
                if result:
                    if (
                        dishln_id
                        in self.component_manager.dishln_gpm_cmd_exe_data
                    ):
                        self.component_manager.dishln_gpm_cmd_exe_data[
                            dishln_id
                        ][band_value] = result
                        self.logger.debug(
                            "dishln gpm %s",
                            self.component_manager.dishln_gpm_cmd_exe_data,
                        )
            if result:
                name = f"{dishln_id}_{band_value}"
                with self.component_manager.command_completion_cond:
                    self.command_results[name] = result
                    cond = self.component_manager.command_completion_cond
                    with cond:
                        cond.notify_all()

        return callback
