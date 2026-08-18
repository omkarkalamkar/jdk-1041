"""Strategy for LoadDishCfg command.
"""
import json
from typing import Tuple

from retry import retry
from ska_telmodel.data import TMData

from ska_tmc_centralnode.utils.config_json_validator import DishConfigValidator

from .contexts import LoadDishCfgRuntimeContext
from .errors import CommandInitializationError, DishVccFetchError
from .load_dish_cfg_plan import LoadDishCfgPlan


class LoadDishCfgStrategy:
    """Build execution plan for LoadDishCfg."""

    def __init__(
        self,
        runtime_context: LoadDishCfgRuntimeContext,
        logger,
        command_id: str,
    ):
        self.runtime_context = runtime_context
        self.logger = logger
        self.command_id = command_id

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
            raise DishVccFetchError(error_message)
        return dish_vcc_map_json, error_message

    def _check_and_validate_dish_vcc_data(
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
        (
            dishid_vcc_map_json,
            _,
        ) = self.fetch_dishid_vcc_map(dishid_vcc_map_params)
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
            self.runtime_context.k_value_valid_range_lower_limit,
            self.runtime_context.k_value_valid_range_upper_limit,
            self.runtime_context.validate_dish_ids,
        )
        is_valid_dish_cfg, message = config_json_validator.is_json_valid()
        return is_valid_dish_cfg, message

    def build(self, argin: str) -> LoadDishCfgPlan:
        (
            dish_vcc_json,
            error,
        ) = self._check_and_validate_dish_vcc_data(argin)

        if error:
            raise CommandInitializationError(error)

        return LoadDishCfgPlan(
            dish_cfg_params=argin,
            dish_vcc_config_json=dish_vcc_json,
            dish_parameters=dish_vcc_json["dish_parameters"],
        )
