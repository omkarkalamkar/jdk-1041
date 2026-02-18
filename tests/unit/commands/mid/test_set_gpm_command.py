"""Test cases for SetGlobalPointingModel command"""

import json
import threading
from threading import RLock
from unittest.mock import MagicMock, call, patch

import mock
import pytest
from ska_control_model import TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tango_testing.mock.placeholders import Anything
from ska_tmc_common import DevFactory
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)

from ska_tmc_centralnode.commands.set_global_pointing_model import (
    SetGlobalPointingModel,
)
from ska_tmc_centralnode.manager.aggregators import DishAttrValueAggregator
from ska_tmc_centralnode.model.enum import DishConfigStatus
from tests.settings import MID_SUBARRAY_DEVICE, create_cm, logger

gpm_default_paths = {
    "version": "2.0",
    "interface": "https://schema.skao.int/ska-mid-global-pointing-model/1.0",
    "data_sources_prefix": "car://gitlab.com/ska-telescope/ska-tmc/ska-tmc-simulators",
    "file_path_prefix": "instrument/ska_mid1/global_pointing_model_data",
}

gpm_input = {
    "version": "1.0",
    "receptors": {
        "SKA001": ["Band_4"],
    },
}


def test_gpm_paths_from_receptors():
    """Test to check the command function"""
    cm, _ = create_cm()
    adapter_factory = HelperAdapterFactory()
    set_gpm = SetGlobalPointingModel(cm, adapter_factory, logger)
    dictionary = set_gpm.form_gpm_path_from_receptors(gpm_input)
    assert type(dictionary) is dict
    assert "interface" in dictionary["ska001"][0].keys()
    assert "tm_data_sources" in dictionary["ska001"][0].keys()
    assert "tm_data_filepath" in dictionary["ska001"][0].keys()


def test_form_gpm_file_for_each_dish():
    """Test to check the command function"""
    cm, _ = create_cm()
    cm.gpm_unknown_dishes = ["ska001"]
    dish_params = cm.get_default_gpm_version_params()
    adapter_factory = HelperAdapterFactory()
    set_gpm = SetGlobalPointingModel(
        component_manager=cm, adapter_factory=adapter_factory, logger=logger
    )
    gpm_data = set_gpm.form_gpm_file_for_each_dish(
        ["gpm-ska001-Band_1.json"],
        dish_params,
    )
    assert type(gpm_data) is dict
    assert "interface" in gpm_data["ska001"][0].keys()
    assert "tm_data_filepath" in gpm_data["ska001"][0].keys()
    assert "tm_data_sources" in gpm_data["ska001"][0].keys()
    assert gpm_data["ska001"][0]["interface"]
    assert gpm_data["ska001"][0]["tm_data_filepath"]
    assert gpm_data["ska001"][0]["tm_data_sources"]


def test_get_gpm_files():
    """Test to check the command function"""
    cm, _ = create_cm()
    cm.gpm_unknown_dishes = ["ska001"]
    dish_params = cm.get_default_gpm_version_params()
    adapter_factory = HelperAdapterFactory()
    set_gpm = SetGlobalPointingModel(
        component_manager=cm, adapter_factory=adapter_factory, logger=logger
    )
    gpm_data = set_gpm.get_gpm_files(dish_params)
    assert gpm_data
    assert type(gpm_data) is list


def test_set_gpm_do_method(tango_context):
    """Test to check the command function"""

    input = {
        "ska001": [
            {
                "interface": "https://schema.skao.int/",
                "tm_data_sources": "car://gitlab.com/ska-telescope/ska-tmc",
                "tm_data_filepath": "gpm-ska001-Band_4.json",
            }
        ]
    }
    cm, _ = create_cm()
    cm.gpm_unknown_dishes = ["ska001"]
    adapter_factory = HelperAdapterFactory()
    set_gpm = SetGlobalPointingModel(
        component_manager=cm, adapter_factory=adapter_factory, logger=logger
    )
    result, _ = set_gpm.do(input)
    result == ResultCode.QUEUED

    input2 = {
        "ska093": [
            {
                "interface": "https://schema.skao.int/",
                "tm_data_sources": "car://gitlab.com/ska-telescope/ska-tmc",
                "tm_data_filepath": "gpm-ska001-Band_4.json",
            }
        ]
    }

    result, _ = set_gpm.do(input2)
    result == ResultCode.FAILED

    dev_factory = DevFactory()
    sa = dev_factory.get_device(MID_SUBARRAY_DEVICE)
    sa.SetDirectassignedResources(["SKA036"])
    result, _ = set_gpm.do(input2)
    result == ResultCode.FAILED

    set_gpm.add_data_to_gpm_dictionary_in_case_of_error("ska001", "error")
    assert "ska001" in cm.dishln_gpm_cmd_exe_data.keys()
    assert "ERROR: error" == cm.dishln_gpm_cmd_exe_data["ska001"]


def test_set_gpm_command_with_ok(
    tango_context,
    task_callback,
):
    """Test SetGlobalPointingModel command with successful completion"""
    cm, _ = create_cm()
    adapter_factory = HelperAdapterFactory()
    set_gpm_command = SetGlobalPointingModel(
        component_manager=cm,
        adapter_factory=adapter_factory,
        logger=logger,
    )

    # Set up the component manager's gpm data
    cm.dishln_gpm_cmd_exe_data = {
        "ska001": {"Band_4": [0, "Command Completed"]}
    }

    # Mock the _set_gpm_to_dish to avoid actual device calls
    with patch.object(
        set_gpm_command,
        "_set_gpm_to_dish",
        return_value=([ResultCode.OK], []),
    ):
        # Mock wait_for_command_completion to complete immediately
        with patch.object(
            set_gpm_command,
            "wait_for_command_completion",
            return_value=(ResultCode.OK, ""),
        ):
            result, message = set_gpm_command.apply_gpm(
                dish_gpm_params=json.dumps(gpm_input),
                logger=logger,
                task_callback=task_callback,
                task_abort_event=threading.Event(),
            )

    # Verify the result
    assert result == ResultCode.OK

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


def test_apply_gpm_no_receptors_and_empty_gpm_files():
    cm, _ = create_cm()
    cm.reset_gpm_data = MagicMock()
    mock_logger = MagicMock()
    adapter_factory = HelperAdapterFactory()
    instance = SetGlobalPointingModel(
        component_manager=cm,
        adapter_factory=adapter_factory,
        logger=mock_logger,
    )
    task_callback = MagicMock()
    dish_gpm_params = {"version": "1.0", "interface": "ska.test.Interface"}

    with patch.object(instance, "get_gpm_files", return_value=[]):
        instance.apply_gpm(
            json.dumps(dish_gpm_params),
            logger,
            task_callback=task_callback,
            task_abort_event=threading.Event(),
        )

        calls = [
            call(status=TaskStatus.IN_PROGRESS),
            call(
                status=TaskStatus.COMPLETED,
                result=(
                    ResultCode.FAILED,
                    "No GPM files found on set GPM parameters.",
                ),
                exception="No GPM files found on set GPM parameters.",
            ),
        ]

        task_callback.assert_has_calls(calls)
        instance.component_manager.reset_gpm_data.assert_called_once()
        mock_logger.debug.assert_called_once_with(
            "Error message: %s", "No GPM files found on set GPM parameters."
        )


def test_process_update_task_for_command_failure():
    adapter_factory = HelperAdapterFactory()
    mock_component_manager = MagicMock()
    mock_component_manager.dishln_gpm_cmd_exe_data = {
        "ska001": "Dish is unreachable",
        "ska002": "Error connecting to dish",
    }
    mock_component_manager.global_pointing_model_status = {}

    command = SetGlobalPointingModel(
        component_manager=mock_component_manager,
        adapter_factory=adapter_factory,
        logger=MagicMock(),
    )
    command.task_callback = MagicMock()

    error_message = "Command failed"
    command.process_update_task_for_command_failure(error_message)

    expected_error_message = error_message + str(
        mock_component_manager.dishln_gpm_cmd_exe_data
    )

    command.task_callback.assert_called_once_with(
        status=TaskStatus.COMPLETED,
        result=(ResultCode.FAILED, expected_error_message),
        exception=expected_error_message,
    )


def test_no_gpm_executed():
    component_manager = MagicMock()
    adapter_factory = HelperAdapterFactory()
    component_manager.number_of_gpm_executed = 0
    command = SetGlobalPointingModel(
        component_manager=component_manager,
        adapter_factory=adapter_factory,
        logger=MagicMock(),
    )
    result_code, result_message = command._set_gpm_to_dish({})
    assert component_manager.gpm_version_aggregated_result == ResultCode.OK

    assert result_code == [ResultCode.UNKNOWN]
    assert result_message == []


def test_set_gpm_to_dish_exception_handling():
    dish_adapter = MagicMock(dev_name="ska001")
    component_manager = MagicMock()
    component_manager.dish_adapters = [dish_adapter]
    component_manager.is_already_assigned.side_effect = (
        lambda dish_id: dish_id not in {"ska001", "SKA001"}
    )
    adapter_factory = HelperAdapterFactory()
    logger = MagicMock()
    command = SetGlobalPointingModel(
        component_manager=component_manager,
        adapter_factory=adapter_factory,
        logger=logger,
    )
    command.dish_adapters = component_manager.dish_adapters
    gpm_data = {
        "ska001": [
            {
                "interface": "https://schema.skao.int",
                "tm_data_sources": "car://gitlab.com/ska-telescope/ska-tmc",
                "tm_data_filepath": "gpm-ska001-Band_4.json",
            }
        ]
    }
    with patch.object(
        command, "invoke_command", side_effect=Exception("Test error")
    ) as mock_send_command:
        result_code, result_message = command._set_gpm_to_dish(gpm_data)
    mock_send_command.assert_called_once()
    logger.exception.assert_called_once()
    assert result_code == [ResultCode.FAILED]
    assert result_message == [
        "Error in Calling ApplyPointingModel command on dish adapter Test error"
    ]


@pytest.mark.skip("removed")
def test_update_set_gpm_results():
    cm, _ = create_cm()
    cm.dishln_gpm_lock = RLock()
    cm.dishln_gpm_cmd_exe_data = {"ska001": {"Band_1": None}}
    cm.number_of_gpm_executed = 1
    cm.command_in_progress = "SetGlobalPointingModel"
    cm.gpm_version_aggregated_result = ResultCode.UNKNOWN
    cm.logger = mock.Mock()
    cm._get_band_dishln_gpm_cmd_data = MagicMock(return_value="Band_1")
    dev_name = "mid-tmc/leaf-node-dish/ska001"
    value = (
        "cmd-12345-ApplyPointingModel",
        json.dumps([ResultCode.OK.value, ""]),
    )
    cm.update_set_gpm_results(dev_name, value)
    assert cm.dishln_gpm_cmd_exe_data["ska001"] == {
        "Band_1": [ResultCode.OK.value, ""],
    }
    assert cm.number_of_gpm_executed == 0
    assert cm.gpm_version_aggregated_result == ResultCode.OK


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
