import logging
from unittest.mock import Mock

import pytest

from ska_tmc_centralnode.refactored_commands.load_dish_cfg.dish_k_executor import (
    DishKValueExecutor,
)


class TestDishKValueExecutor:
    """Unit tests for DishKValueExecutor."""

    @pytest.fixture
    def dish_adapter(self):
        """Create a mock dish adapter."""
        adapter = Mock()
        adapter.dev_name = "dish/leaf_node/dish001"
        adapter.proxy = Mock()
        return adapter

    @pytest.fixture
    def second_dish_adapter(self):
        """Create a second mock dish adapter."""
        adapter = Mock()
        adapter.dev_name = "dish/leaf_node/dish002"
        adapter.proxy = Mock()
        return adapter

    @pytest.fixture
    def executor_dependencies(self):
        """Create executor dependencies."""
        return {
            "invoke_callback_factory": Mock(
                return_value=Mock(name="callback")
            ),
            "add_device_command": Mock(),
            "add_device_name": Mock(),
            "update_kvalue_aggregator": Mock(),
            "logger": Mock(spec=logging.Logger),
        }

    @pytest.fixture
    def executor(self, dish_adapter, executor_dependencies):
        """Create DishKValueExecutor."""
        return DishKValueExecutor(
            dish_adapters=[dish_adapter],
            command_id="123-LoadDishCfg",
            **executor_dependencies,
        )

    def test_execute_invokes_set_k_value(
        self,
        executor,
        dish_adapter,
    ):
        """Test SetKValue is invoked for a configured dish."""

        dish_parameters = {
            "dish001": {
                "k": 10,
            }
        }

        executor.execute(dish_parameters)

        dish_adapter.proxy.command_inout_asynch.assert_called_once_with(
            "SetKValue",
            10,
            executor.invoke_callback_factory.return_value,
        )

    def test_execute_adds_device_command(
        self,
        executor,
        dish_adapter,
    ):
        """Test DeviceCommand is created and registered."""

        dish_parameters = {
            "dish001": {
                "k": 10,
            }
        }

        executor.execute(dish_parameters)

        executor.add_device_command.assert_called_once()

        device_command = executor.add_device_command.call_args.args[0]

        assert device_command.device_name == dish_adapter.dev_name
        assert device_command.command_name == "SetKValue"
        assert device_command.command_input == 10

    def test_execute_adds_device_name(
        self,
        executor,
        dish_adapter,
    ):
        """Test invoked dish device is registered."""

        dish_parameters = {
            "dish001": {
                "k": 10,
            }
        }

        executor.execute(dish_parameters)

        executor.add_device_name.assert_called_once_with(dish_adapter.dev_name)

    def test_execute_creates_callback_for_device(
        self,
        executor,
        dish_adapter,
    ):
        """Test callback factory is called with the dish device name."""

        dish_parameters = {
            "dish001": {
                "k": 10,
            }
        }

        executor.execute(dish_parameters)

        executor.invoke_callback_factory.assert_called_once_with(
            dish_adapter.dev_name
        )

    def test_execute_multiple_dishes(
        self,
        dish_adapter,
        second_dish_adapter,
        executor_dependencies,
    ):
        """Test SetKValue is invoked for every configured dish."""

        executor = DishKValueExecutor(
            dish_adapters=[
                dish_adapter,
                second_dish_adapter,
            ],
            command_id="123-LoadDishCfg",
            **executor_dependencies,
        )

        dish_parameters = {
            "dish001": {"k": 10},
            "dish002": {"k": 20},
        }

        executor.execute(dish_parameters)

        dish_adapter.proxy.command_inout_asynch.assert_called_once_with(
            "SetKValue",
            10,
            executor.invoke_callback_factory.return_value,
        )

        second_dish_adapter.proxy.command_inout_asynch.assert_called_once_with(
            "SetKValue",
            20,
            executor.invoke_callback_factory.return_value,
        )

        assert executor.add_device_command.call_count == 2
        assert executor.add_device_name.call_count == 2

    def test_execute_missing_adapter_updates_kvalue_aggregator(
        self,
        executor,
    ):
        """Test missing dish adapter is reported to the aggregator."""

        dish_parameters = {
            "dish999": {
                "k": 10,
            }
        }

        executor.execute(dish_parameters)

        executor.update_kvalue_aggregator.assert_called_once_with(
            "dish999",
            "Adapter not found for dish leaf node dish999",
        )

        executor.add_device_command.assert_not_called()
        executor.add_device_name.assert_not_called()
        executor.invoke_callback_factory.assert_not_called()

    def test_execute_missing_adapter_does_not_invoke_command(
        self,
        executor,
    ):
        """Test no device command is invoked when adapter is missing."""

        executor.execute(
            {
                "dish999": {
                    "k": 15,
                }
            }
        )

        # There is no adapter, therefore no command can be invoked.
        executor.update_kvalue_aggregator.assert_called_once()

    def test_execute_uses_dish_id_suffix_matching(
        self,
        dish_adapter,
        executor_dependencies,
    ):
        """Test adapter is found using device-name suffix."""

        dish_adapter.dev_name = "mid/tm_subarray_leaf_node/dish001"

        executor = DishKValueExecutor(
            dish_adapters=[dish_adapter],
            command_id="123-LoadDishCfg",
            **executor_dependencies,
        )

        executor.execute(
            {
                "dish001": {
                    "k": 30,
                }
            }
        )

        dish_adapter.proxy.command_inout_asynch.assert_called_once()

    def test_execute_with_empty_dish_parameters(
        self,
        executor,
    ):
        """Test execute does nothing for empty configuration."""

        executor.execute({})

        executor.add_device_command.assert_not_called()
        executor.add_device_name.assert_not_called()
        executor.invoke_callback_factory.assert_not_called()
        executor.update_kvalue_aggregator.assert_not_called()

    def test_execute_raises_runtime_error_when_set_k_value_fails(
        self,
        executor,
        dish_adapter,
    ):
        """Test SetKValue invocation exception is wrapped."""

        dish_adapter.proxy.command_inout_asynch.side_effect = RuntimeError(
            "Tango failure"
        )

        with pytest.raises(
            RuntimeError,
            match="Error in calling SetKValue command on "
            "dish adapter Tango failure",
        ):
            executor.execute(
                {
                    "dish001": {
                        "k": 10,
                    }
                }
            )

    def test_execute_does_not_add_device_details_when_invocation_fails(
        self,
        executor,
        dish_adapter,
    ):
        """Test device tracking is not updated when invocation fails."""

        dish_adapter.proxy.command_inout_asynch.side_effect = Exception(
            "Invocation failed"
        )

        with pytest.raises(RuntimeError):
            executor.execute(
                {
                    "dish001": {
                        "k": 10,
                    }
                }
            )

        executor.add_device_command.assert_not_called()
        executor.add_device_name.assert_not_called()

    def test_get_dish_adapter_returns_matching_adapter(
        self,
        executor,
        dish_adapter,
    ):
        """Test _get_dish_adapter returns the correct adapter."""

        result = executor._get_dish_adapter("dish001")

        assert result is dish_adapter

    def test_get_dish_adapter_returns_none_for_unknown_dish(
        self,
        executor,
    ):
        """Test _get_dish_adapter returns None when no adapter exists."""

        result = executor._get_dish_adapter("dish999")

        assert result is None

    def test_get_dish_adapter_is_case_insensitive(
        self,
        executor,
        dish_adapter,
    ):
        """Test _get_dish_adapter handles case-insensitive IDs."""

        result = executor._get_dish_adapter("DISH001")

        assert result is dish_adapter
