import json
import threading
from typing import Callable, Optional

from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_telmodel.data import TMData

from ska_tmc_centralnode.commands.central_node_command import (
    LoadDishCfgCommand,
)
from ska_tmc_centralnode.utils.config_json_validator import DishConfigValidator


class LoadDishCfg(LoadDishCfgCommand):
    """
    A class for CentralNode's LoadDishConfig command.
    Load DishId-VCC map from CAR URI and provide it to Csp Master Leaf Node
    After Validation
    """

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

    def load_dish_cfg(
        self,
        argin,
        logger,
        task_callback: Callable = None,
        task_abort_event: Optional[threading.Event] = None,
    ):
        """:param logger: logger
        :type logger: logging.Logger
        :param task_callback: Update task state, defaults to None
        :type task_callback: Callable, optional
        :param task_abort_event: Check for abort, defaults to None
        :type task_abort_event: Event, optional
        """
        # Indicate that the task has started
        task_callback(status=TaskStatus.IN_PROGRESS)

        ret_code, message = self.do(argin)
        self.logger.info(message)
        if ret_code == ResultCode.FAILED:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=ResultCode.FAILED,
                exception=message,
            )
        else:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=ResultCode.OK,
            )

    def _get_dishid_vcc_map_json(self, initial_params: dict):
        """Get DishId-VCC map json from initial params"""
        data_sources = initial_params["tm_data_sources"]
        tm_data_filepath = initial_params["tm_data_filepath"]
        data = TMData(data_sources)
        return data[tm_data_filepath].get_dict()

    def do(self, argin: str):
        """This command does following
        1. Load content of DishId-VCC mapping file from CAR URI
        2. Validate Json
        3. Invoke command on csp master leaf node with file name as an argument
        """

        result_code, message = self.init_adapters()
        if result_code == ResultCode.FAILED:
            return result_code, message

        try:
            dishid_vcc_map_params = json.loads(argin)
            # TODO validate json
        except Exception as e:
            return (
                ResultCode.FAILED,
                ("Problem in loading the JSON string: %s", e),
            )
        self.logger.info("DishId Vcc Map Params %s", dishid_vcc_map_params)

        dishid_vcc_map_json = self._get_dishid_vcc_map_json(
            dishid_vcc_map_params
        )

        self.logger.info("DishId Vcc Map Json %s", dishid_vcc_map_json)

        config_json_validator = DishConfigValidator(dishid_vcc_map_json)

        if config_json_validator.is_json_valid():
            # TODO return json error message
            self.logger.debug(
                f"Invoking LoadDishCfg command on:{self.csp_mln_adapter}"
            )
            return_code, message_or_unique_id = self.send_command(
                [self.csp_mln_adapter],
                "Error in calling LoadDishCfg command on MCCS Master Leaf Node",
                "LoadDishCfg",
                json.dumps(dishid_vcc_map_params),
            )
            # condition for exception raised during invoking command
            if return_code in [ResultCode.FAILED]:
                return ResultCode.FAILED, message_or_unique_id
            # condition for unavailable devices
            elif return_code in [ResultCode.REJECTED]:
                # return ResultCode.FAILED, message_or_unique_id
                unavailable_device = message_or_unique_id.split(" ")[0]
                self.logger.info(
                    f"Unavailable devices are {unavailable_device}"
                )
                return (
                    ResultCode.OK,
                    f"Unavailable devices are {unavailable_device}",
                )
            self.logger.debug(
                f"Successfully Invoked LoadDishCfg command on:{self.csp_mln_adapter}"
            )
            return (ResultCode.OK, "")

        return (
            ResultCode.FAILED,
            "DishId Vcc map json is invalid",
        )
