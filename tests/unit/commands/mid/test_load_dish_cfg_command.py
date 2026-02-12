"""Test module for command load dish cfg"""

import json
from unittest.mock import patch

import mock
import tango
from ska_control_model import TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tmc_common import DevFactory
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)
from tango import ApiUtil

from ska_tmc_centralnode.commands.load_dish_config_command import LoadDishCfg
from ska_tmc_centralnode.model.enum import DishConfigStatus
from tests.settings import MID_CSP_MLN_DEVICE, create_cm, logger

# Helper Dish LN device is using Database API and in Unit test Database API
# is not callable
# Patch this particular method which mock return value from SetKValue command


@patch.object(LoadDishCfg, "_set_k_numbers_to_dish")
def test_load_dish_cfg_command(
    _set_k_numbers_to_dish,
    tango_context,
    task_callback,
    json_factory,
):
    """Test load dish cfg invoke on devices with task status as completed"""
    # This need to be set to enable async command callback event
    ApiUtil.instance().set_asynch_cb_sub_model(
        tango.cb_sub_model.PUSH_CALLBACK
    )
    logger.info("%s", tango_context)
    cm, _ = create_cm()
    _set_k_numbers_to_dish.return_value = ([ResultCode.QUEUED], [""])
    cm.is_dish_vcc_config_set = True

    dish_cfg_input_str = json_factory("command_load_dish_cfg")
    cm.load_dish_cfg(dish_cfg_input_str, task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.OK, "Command Completed"),
        },
        lookahead=20,
    )
    assert cm.dish_vcc_command_status == DishConfigStatus.COMPLETED
    # Validate memorizedDishVccMap attribute set
    dev_factory = DevFactory()
    csp_mln = dev_factory.get_device(MID_CSP_MLN_DEVICE)
    assert csp_mln.memorizedDishVccMap == dish_cfg_input_str


def test_load_dish_cfg_command_invalid_json(
    tango_context, task_callback, json_factory, set_mid_sdp_csp_admin_modes
):
    """Test LoadDishCfg command rejected when invalid json provided"""
    logger.info("%s", tango_context)
    cm, _ = create_cm()
    cm.is_dish_vcc_config_set = True
    cm.is_command_allowed("LoadDishCfg")
    dish_cfg_input_str = json_factory("command_load_dish_cfg")

    dish_cfg_input = json.loads(dish_cfg_input_str)
    dish_cfg_input.pop("tm_data_sources")

    result_code, message = cm.load_dish_cfg(
        json.dumps(dish_cfg_input), task_callback=task_callback
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (
                ResultCode.FAILED,
                "tm_data_sources and tm_data_filepath not provided in json",
            ),
            "exception": "tm_data_sources and tm_data_filepath not provided in json",
        },
    )


def test_load_dish_cfg_command_kvalue_out_of_range(
    tango_context, task_callback, json_factory, set_mid_sdp_csp_admin_modes
):
    """Test LoadDishCfg command rejected when kvalue is out of range"""
    logger.info("%s", tango_context)
    cm, _ = create_cm()
    cm.is_dish_vcc_config_set = True
    cm.is_command_allowed("LoadDishCfg")
    dish_cfg_input_str = json_factory("load_dish_cfg_kvalue_out_of_range")
    result_code, message = cm.load_dish_cfg(
        dish_cfg_input_str, task_callback=task_callback
    )
    exception_message = "K values are not in range (1 to 1177)"
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (
                ResultCode.FAILED,
                exception_message,
            ),
            "exception": exception_message,
        },
    )


def test_load_dish_cfg_command_invalid_file_name(
    tango_context, task_callback, json_factory, set_mid_sdp_csp_admin_modes
):
    """Test LoadDishCfg command rejected when invalid json provided"""
    logger.info("%s", tango_context)
    cm, _ = create_cm()
    cm.is_dish_vcc_config_set = True
    cm.is_command_allowed("LoadDishCfg")
    dish_cfg_input_str = json_factory("command_load_dish_cfg_invalid")

    dish_cfg_input = json.loads(dish_cfg_input_str)

    result_code, message = cm.load_dish_cfg(
        json.dumps(dish_cfg_input), task_callback=task_callback
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (
                ResultCode.FAILED,
                "Error in Loading Dish VCC map json file 'No telescope model "
                + "data with key instrument/dishid_vcc_map_configuration/"
                + "mid_cbf_initial_parameters_invalid.json exists!'",
            ),
            "exception": "Error in Loading Dish VCC map json file 'No "
            + "telescope model data with key instrument/dishid_vcc_map_"
            + "configuration/mid_cbf_initial_parameters_invalid.json exists!'",
        },
    )


def test_dish_vcc_validation_status(task_callback, json_factory):
    """Test dish vcc validation result of component manager"""

    cm, _ = create_cm()
    cm.dish_vcc_command_status = DishConfigStatus.STAGING
    cm.handle_dish_vcc_validation_result(MID_CSP_MLN_DEVICE, ResultCode.OK)
    assert cm.dish_vcc_command_status == DishConfigStatus.COMPLETED
    assert json.loads(cm.dish_vcc_validation_status) == {
        "mid-tmc/leaf-node-csp/0": "TMC and CSP Master Dish Vcc Version is Same"
    }

    cm.handle_dish_vcc_validation_result(MID_CSP_MLN_DEVICE, ResultCode.FAILED)
    assert json.loads(cm.dish_vcc_validation_status) == {
        "mid-tmc/leaf-node-csp/0": "TMC and CSP Master Dish VCC version is Different"
    }

    cm.handle_dish_vcc_validation_result(
        MID_CSP_MLN_DEVICE, ResultCode.NOT_ALLOWED
    )
    assert json.loads(cm.dish_vcc_validation_status) == {
        "mid-tmc/leaf-node-csp/0": "CSP Master device is unavailable"
    }
    # Validate Dish Config status flag
    cm.check_if_csp_all_dish_ready = mock.Mock()
    cm.check_if_csp_all_dish_ready.return_value = True
    cm.invoke_load_dish_cfg_command_callback = mock.Mock()
    cm.handle_dish_vcc_validation_result(
        MID_CSP_MLN_DEVICE, ResultCode.UNKNOWN
    )
    assert cm.dish_vcc_command_status == DishConfigStatus.INIT

    cm.check_if_csp_all_dish_ready.return_value = False
    cm.command_in_progress = ""
    cm.handle_dish_vcc_validation_result(
        MID_CSP_MLN_DEVICE, ResultCode.UNKNOWN
    )

    assert cm.dish_vcc_command_status == DishConfigStatus.FAILED


def test_load_dish_cnfg_command_fail_csp_master(
    tango_context, json_factory, set_mid_sdp_csp_admin_modes
):
    cm, _ = create_cm()
    adapter_factory = HelperAdapterFactory()
    attrs = {"LoadDishCfg.side_effect": Exception}
    cspmastermock = mock.Mock(**attrs)
    adapter_factory.get_or_create_adapter(
        MID_CSP_MLN_DEVICE, proxy=cspmastermock
    )
    dish_cfg_input_str = json_factory("command_load_dish_cfg")
    load_dish_cnfg_command = LoadDishCfg(cm, adapter_factory, logger=logger)
    (
        load_dish_cnfg_command.dish_vcc_config_json,
        _,
    ) = load_dish_cnfg_command.check_and_validate_dish_vcc_data(
        dish_cfg_input_str
    )
    (res_code, _) = load_dish_cnfg_command.do(dish_cfg_input_str)
    assert res_code == ResultCode.FAILED


def test_load_dish_config_command_fail(
    tango_context, json_factory, task_callback, set_mid_sdp_csp_admin_modes
):
    # Validate load dish cfg is rejected if dish vcc process status
    # is in progress
    cm, _ = create_cm()
    cm.dish_vcc_command_status = DishConfigStatus.IN_PROGRESS
    cm.is_command_allowed("LoadDishCfg")
    dish_cfg_input_str = json_factory("command_load_dish_cfg_invalid")

    dish_cfg_input = json.loads(dish_cfg_input_str)

    cm.load_dish_cfg(json.dumps(dish_cfg_input), task_callback=task_callback)

    task_callback.assert_against_call(
        status=TaskStatus.REJECTED,
        result=(
            ResultCode.NOT_ALLOWED,
            "Dish Vcc Configuration is in Progress. Dish Vcc command status: IN_PROGRESS",
        ),
    )
