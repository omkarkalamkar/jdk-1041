"""Test cases for SetGlobalPointingModel command"""

import json
import threading
from unittest.mock import MagicMock, patch

import mock
import pytest
from ska_control_model import TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tango_testing.mock.placeholders import Anything
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)

from ska_tmc_centralnode.manager.aggregators import DishAttrValueAggregator
from ska_tmc_centralnode.model.enum import DishConfigStatus
from ska_tmc_centralnode.refactored_commands.set_gpm.set_gpm_command import (
    SetGlobalPointingModel,
)
from ska_tmc_centralnode.refactored_commands.set_gpm.strategy import (
    GPMPlan,
    GPMStrategy,
)
from tests.settings import create_cm

gpm_input = {
    "version": "1.0",
    "receptors": {
        "SKA001": ["Band_4"],
    },
}

gpm_default_paths = {
    "version": "1.0.0",
    "tm_data_sources": [
        "car://gitlab.com/ska-telescope/ska-tmc/ska-tmc-simulators"
    ],
    "tm_data_filepath": "instrument/ska_mid1/global_pointing_model_data",
}


def test_gpm_paths_from_receptors():
    """Test to check the command function"""

    set_gpm = GPMStrategy(
        logger=MagicMock(),
        default_gpm_version_params=gpm_default_paths,
        gpm_unknown_dishes=[],
    )
    dictionary, _ = set_gpm.form_gpm_path_from_receptors(gpm_input)
    assert type(dictionary) is dict
    assert "tm_data_sources" in dictionary["ska001"][0].keys()
    assert "tm_data_filepath" in dictionary["ska001"][0].keys()


def test_form_gpm_file_for_each_dish():
    """Test to check the command function"""

    set_gpm = GPMStrategy(
        logger=MagicMock(),
        default_gpm_version_params=gpm_default_paths,
        gpm_unknown_dishes=["ska001"],
    )
    gpm_data, _ = set_gpm.form_gpm_file_for_each_dish(
        ["gpm-ska001-Band_1.json"],
        gpm_default_paths,
    )
    assert type(gpm_data) is dict
    assert "tm_data_filepath" in gpm_data["ska001"][0].keys()
    assert "tm_data_sources" in gpm_data["ska001"][0].keys()
    assert gpm_data["ska001"][0]["tm_data_filepath"]
    assert gpm_data["ska001"][0]["tm_data_sources"]


def test_get_gpm_files():
    """Test to check the command function"""

    cm, _ = create_cm()
    adapter_factory = HelperAdapterFactory()
    set_gpm = SetGlobalPointingModel(
        command_runtime_context=cm._get_gpm_context(),
        adapter_provider=adapter_factory,
        logger=MagicMock(),
    )
    gpm_data = set_gpm.get_gpm_files(gpm_default_paths)
    assert gpm_data
    assert type(gpm_data) is list


def test_set_gpm_command_with_ok(
    tango_context,
    task_callback,
):
    """Test SetGlobalPointingModel command with successful completion"""
    cm, _ = create_cm()
    cm.get_default_gpm_version_params = mock.Mock(
        return_value=gpm_default_paths
    )
    cm.get_default_gpm_version_params()
    with mock.patch.object(
        SetGlobalPointingModel,
        "validate_dishes",
        side_effect=lambda gpm_data: gpm_data,
    ):
        cm.set_gpm_version(
            argin=json.dumps(gpm_input),
            task_callback=task_callback,
            task_abort_event=threading.Event(),
        )
        # Verify task callback was called with correct status transitions
        task_callback.assert_against_call(
            call_kwargs={"status": TaskStatus.IN_PROGRESS}
        )
        task_callback.assert_against_call(
            call_kwargs={
                "status": TaskStatus.COMPLETED,
                "result": (ResultCode.OK, Anything),
            },
            lookahead=2,
        )


def test_apply_gpm_no_receptors_and_empty_gpm_files(
    tango_context, task_callback
):
    gpm_input = {
        "version": "0.0.2",
        "tm_data_sources": [
            "car://gitlab.com/ska-telescope/ska-tmc/ska-tmc-simulators"
        ],
        "tm_data_filepath": "instrument/ska_mid1/global_pointing_model_data",
    }
    cm, _ = create_cm()
    cm.get_default_gpm_version_params = mock.Mock(
        return_value=gpm_default_paths
    )
    cm.get_default_gpm_version_params()
    with mock.patch.object(
        SetGlobalPointingModel,
        "validate_dishes",
        side_effect=lambda gpm_data: gpm_data,
    ):
        cm.set_gpm_version(
            argin=json.dumps(gpm_input),
            task_callback=task_callback,
            task_abort_event=threading.Event(),
        )
        # Verify task callback was called with correct status transitions
        task_callback.assert_against_call(
            call_kwargs={"status": TaskStatus.IN_PROGRESS}
        )
        result = task_callback.assert_against_call(status=TaskStatus.COMPLETED)
        err_msg = "No GPM files found on set GPM parameters."
        exception_msg = result["exception"]
        assert ResultCode.FAILED == result["result"][0]
        assert err_msg in result["result"][1]
        assert err_msg in exception_msg


def test_process_update_task_for_command_failure():
    command_runtime_context = MagicMock()
    adapter_factory = HelperAdapterFactory()
    command_runtime_context.dishln_gpm_cmd_exe_data = {
        "ska001": "Dish is unreachable",
        "ska002": "Error connecting to dish",
    }
    command_runtime_context.global_pointing_model_status = {}

    command = SetGlobalPointingModel(
        command_runtime_context=command_runtime_context,
        adapter_provider=adapter_factory,
        logger=MagicMock(),
    )
    command.context.task_callback = MagicMock()
    error_message = "SetGPM failed on: "
    command.process_update_task_status()

    expected_error_message = error_message + str(
        command_runtime_context.dishln_gpm_cmd_exe_data
    )

    command.context.task_callback.assert_called_once_with(
        status=TaskStatus.COMPLETED,
        result=(ResultCode.FAILED, expected_error_message),
        exception=expected_error_message,
    )


def test_set_gpm_to_dish_exception_handling():
    """Test SetGlobalPointingModel command exception handling during device command building"""
    command_runtime_context = MagicMock()
    command_runtime_context.dishln_gpm_cmd_exe_data = {"ska001": {}}
    command_runtime_context.get_dish_leaf_node_device_names.return_value = [
        "mid-tmc/leaf-node-dish/ska001"
    ]
    adapter_factory = HelperAdapterFactory()
    logger = MagicMock()

    command = SetGlobalPointingModel(
        command_runtime_context=command_runtime_context,
        adapter_provider=adapter_factory,
        logger=logger,
    )
    command.context = MagicMock()
    command.context.device_commands = []
    command._plan = GPMPlan(
        apm_payload={
            "ska001": [
                {
                    "interface": "https://schema.skao.int",
                    "tm_data_sources": "car://gitlab.com/ska-telescope/ska-tmc",
                    "tm_data_filepath": "gpm-ska001-Band_4.json",
                }
            ]
        }
    )
    with patch.object(
        command, "_build_device_command", side_effect=Exception("Test error")
    ):
        command.build_device_commands()
    logger.exception.assert_called_once()
    assert command.context.device_commands == []


def test_handle_gpm_version():
    cm, _ = create_cm()
    dish_id = "ska001"
    cm.gpm_unknown_dishes = [dish_id]
    cm.command_in_progress = ""
    cm._dish_vcc_command_status = DishConfigStatus.COMPLETED
    cm.invoke_set_gpm_command_callback = MagicMock()
    cm.logger = MagicMock()
    cm.check_if_csp_all_dish_ready = MagicMock(return_value=True)
    gpm_version = json.dumps(
        {
            "Band_1": "UNKNOWN",
        }
    )
    cm.global_pointing_model_status[dish_id] = json.loads(gpm_version)
    cm.command_in_progress = ""
    cm.is_gpm_init = False
    cm.handle_gpm_version_event(
        dev_name=f"mid-tmc/leaf-node-dish/{dish_id}", gpmVersion=gpm_version
    )
    assert cm.invoke_set_gpm_command_callback.called


@pytest.mark.parametrize(
    "status, expected_result",
    [
        ({}, []),
        ({"ska001": {"Band1": "SET", "Band2": "SET"}}, []),
        ({"ska001": {"Band1": "UNKNOWN", "Band2": "SET"}}, []),
        ({"ska001": {"Band1": "UNKNOWN", "Band2": "UNKNOWN"}}, ["ska001"]),
        ({"ska001": {"Band1": "UNKNOWN", "Band2": "UNKNOWN"}}, ["ska001"]),
        (
            {
                "ska001": {"Band1": "UNKNOWN", "Band2": "UNKNOWN"},
                "ska002": {"Band1": "SET", "Band2": "SET"},
                "ska003": {"Band1": "UNKNOWN", "Band2": "SET"},
            },
            ["ska001"],
        ),
        ({"ska001": "UNKNOWN"}, []),
        (
            {
                "ska001": {"Band1": "UNKNOWN", "Band2": "UNKNOWN"},
                "ska002": {"Band1": "UNKNOWN", "Band2": "UNKNOWN"},
                "ska003": {"Band1": "UNKNOWN", "Band2": "UNKNOWN"},
            },
            ["ska001", "ska002", "ska003"],
        ),
        ({"ska001": {"Band1": "UNKNOWN", "Band2": "UNKNOWN"}}, ["ska001"]),
    ],
)
def test_aggregate_gpm(status, expected_result):
    cm, _ = create_cm()
    cm.input_parameter.dish_leaf_node_dev_names = list(status.keys())
    cm.global_pointing_model_status = status

    daggr = DishAttrValueAggregator(cm=cm, logger=MagicMock())
    result = daggr.aggregate_gpm()
    assert result == expected_result
