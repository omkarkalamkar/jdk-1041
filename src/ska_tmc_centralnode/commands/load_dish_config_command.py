import json
import threading
from typing import Callable, Optional, Tuple

from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_telmodel.data import TMData

from ska_tmc_centralnode.commands.central_node_command import (
    LoadDishCfgCommand,
)


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
        argin: str,
        logger=None,
        task_callback: Callable = None,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:
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

    def get_dishid_vcc_map_json(self, initial_params: dict) -> dict:
        """Get DishId-VCC map json from initial params
        :param initial_param: this param containg tm data source uri
        and file path which is used for extracting vcc_map json file
        """
        data_sources = initial_params["tm_data_sources"]
        tm_data_filepath = initial_params["tm_data_filepath"]
        data = TMData(data_sources)
        return data[tm_data_filepath].get_dict()

    def do(self, argin: str) -> Tuple[ResultCode, str]:
        """This command does following
        1. Load content of DishId-VCC mapping file from CAR URI
        2. Validate Json
        3. Invoke command on csp master leaf node
        4. Invoke SetKValue command on Dish Leaf Node for each dish id
        provided in dishid_vcc map
        :param argin: dishid vcc map params
        """

        result_code, message = self.init_adapters()
        if result_code == ResultCode.FAILED:
            return result_code, message

        dishid_vcc_map_params = json.loads(argin)
        self.logger.info("DishId Vcc Map Params %s", dishid_vcc_map_params)

        dishid_vcc_map_json = self.get_dishid_vcc_map_json(
            dishid_vcc_map_params
        )

        self.logger.info("DishId Vcc Map Json %s", dishid_vcc_map_json)
        dish_parameters = dishid_vcc_map_json.get("dish_parameters")
        unavailable_devices = []
        for return_codes, message_or_unique_ids in [
            self._invoke_load_dish_cfg_on_csp_master_ln(dishid_vcc_map_params),
            self._set_k_numbers_to_dish(dish_parameters),
        ]:
            for return_code, message_or_unique_id in zip(
                return_codes, message_or_unique_ids
            ):
                # condition for exception raised during invoking command
                if return_code in [ResultCode.FAILED]:
                    self.logger.info(
                        "Invocation of command LoadDishCfg failed with error %s",
                        message_or_unique_id,
                    )
                    return ResultCode.FAILED, message_or_unique_id
                # condition for unavailable devices
                elif return_code in [ResultCode.REJECTED]:
                    # return ResultCode.FAILED, message_or_unique_id
                    unavailable_devices.append(
                        message_or_unique_id.split(" ")[0]
                    )
        if unavailable_devices:
            self.logger.info(f"Unavailable devices are {unavailable_devices}")
            return (
                ResultCode.OK,
                f"Unavailable devices are {unavailable_devices}",
            )
        self.logger.info(
            f"Successfully Invoked LoadDishCfg command on:{self.csp_mln_adapter.dev_name}"
        )
        return (ResultCode.OK, "")

    def _invoke_load_dish_cfg_on_csp_master_ln(
        self, dishid_vcc_map_params: str
    ) -> Tuple[ResultCode, list]:
        """Invoke LoadDishCfg command on Csp Master with vcc_map_params argument
        :param dishid_vcc_map_params: vcc_map_params info containing vcc_dish mapping
        """
        self.logger.debug(
            f"Invoking LoadDishCfg command on:{self.csp_mln_adapter.dev_name}"
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
                        "Invoking SetKValue on dish adapter %s",
                        dish_adapter.dev_name,
                    )
                    return_code, message_or_unique_id = self.send_command(
                        [dish_adapter],
                        f"Error in calling SetKValue command on dish adapter {dish_adapter.dev_name}",
                        "SetKValue",
                        k_value,
                    )
                    return_codes.append(return_code[0])
                    message_or_unique_ids.append(message_or_unique_id[0])
                else:
                    error_message = (
                        f"Dish adapter not found for dish id {dish_id}"
                    )
                    self.logger.info(error_message)
        except Exception as e:
            self.logger.info(
                "Error in Calling setKvalue command on dish adapter %s", e
            )
            return [ResultCode.FAILED], [
                f"Error in Calling setKvalue command on dish adapter {e}"
            ]

        return return_codes, message_or_unique_ids
