"""Executor for invoking SetKValue commands on Dish Leaf Nodes."""

import logging
from typing import Any, Callable

from ska_tmc_common.adapter_type import AdapterType
from ska_tmc_common.v4.command_context import DeviceCommand

LOGGER = logging.getLogger(__name__)


class DishKValueExecutor:
    """
    Handles device-level SetKValue execution for LoadDishCfg.

    Responsibilities:
        - Find the adapter corresponding to a dish ID.
        - Invoke SetKValue asynchronously.
        - Create and register the corresponding DeviceCommand.
        - Track the invoked dish device.
        - Update K-value validation results when an adapter is missing.

    This class does not handle the overall LoadDishCfg command result.
    """

    def __init__(
        self,
        dish_adapters: list[Any],
        command_id: str,
        invoke_callback_factory: Callable[[str], Callable],
        add_device_command: Callable[[DeviceCommand], None],
        add_device_name: Callable[[str], None],
        update_kvalue_aggregator: Callable[[str, str], None],
        logger: logging.Logger = LOGGER,
    ):
        self.dish_adapters = dish_adapters
        self.command_id = command_id
        self.invoke_callback_factory = invoke_callback_factory
        self.add_device_command = add_device_command
        self.add_device_name = add_device_name
        self.update_kvalue_aggregator = update_kvalue_aggregator
        self.logger = logger

    def execute(self, dish_parameters: dict) -> None:
        """
        Invoke SetKValue for all configured dishes.

        Args:
            dish_parameters:
                Mapping of dish IDs to their VCC/K-value configuration.
        """
        for dish_id, vcc_k_map in dish_parameters.items():
            self._execute_for_dish(
                dish_id=dish_id,
                vcc_k_map=vcc_k_map,
            )

    def _execute_for_dish(
        self,
        dish_id: str,
        vcc_k_map: dict,
    ) -> None:
        """
        Invoke SetKValue for a single dish.

        Args:
            dish_id: Dish identifier.
            vcc_k_map: VCC/K-value configuration for the dish.
        """
        dish_adapter = self._get_dish_adapter(dish_id)

        if dish_adapter is None:
            error_message = f"Adapter not found for dish leaf node {dish_id}"

            self.logger.error(
                "Command ID: %s | %s",
                self.command_id,
                error_message,
            )

            self.update_kvalue_aggregator(
                dish_id.lower(),
                error_message,
            )
            return

        k_value = vcc_k_map.get("k")

        self.logger.debug(
            "Command ID: %s | Invoking SetKValue command on: %s",
            self.command_id,
            dish_adapter.dev_name,
        )

        try:
            callback = self.invoke_callback_factory(dish_adapter.dev_name)

            dish_adapter.proxy.command_inout_asynch(
                "SetKValue",
                k_value,
                callback,
            )

            self._add_device_command(
                dish_adapter.dev_name,
                k_value,
            )

            self.add_device_name(dish_adapter.dev_name)

        except Exception as exception:
            self.logger.exception(
                "Command ID: %s | Exception occurred in calling "
                "SetKValue on %s",
                self.command_id,
                dish_adapter.dev_name,
            )

            raise RuntimeError(
                "Error in calling SetKValue command on "
                f"dish adapter {exception}"
            ) from exception

    def _add_device_command(
        self,
        device_name: str,
        k_value: Any,
    ) -> None:
        """
        Create and register DeviceCommand for SetKValue.

        Args:
            device_name: Dish Leaf Node device name.
            k_value: K-value passed to SetKValue.
        """
        device_command = DeviceCommand(
            device_name=device_name,
            command_name="SetKValue",
            adapter_type=AdapterType.DISH,
            command_input=k_value,
        )

        self.add_device_command(device_command)

    def _get_dish_adapter(
        self,
        dish_id: str,
    ) -> Any | None:
        """
        Find the adapter corresponding to a dish ID.

        Args:
            dish_id: Dish identifier.

        Returns:
            Matching dish adapter, or None if no adapter exists.
        """
        dish_id = dish_id.lower()

        return next(
            (
                adapter
                for adapter in self.dish_adapters
                if adapter.dev_name.lower().endswith(dish_id)
            ),
            None,
        )
