import json

import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common import DevFactory
from tango import ApiUtil

from tests.settings import MID_CSP_MLN_DEVICE, create_cm, logger


def test_load_dish_cfg_command(tango_context, task_callback, json_factory):
    """Test load dish cfg invoke on devices with task status as completed"""
    # This need to be set to enable async command callback event
    ApiUtil.instance().set_asynch_cb_sub_model(
        tango.cb_sub_model.PUSH_CALLBACK
    )
    logger.info("%s", tango_context)
    cm, _ = create_cm()
    cm.is_command_allowed("LoadDishCfg")
    dish_cfg_input_str = json_factory("command_load_dish_cfg")
    cm.load_dish_cfg(dish_cfg_input_str, task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.COMPLETED, "result": ResultCode.OK},
        lookahead=5,
    )
    # Validate memorizedDishVccMap attribute set
    dev_factory = DevFactory()
    csp_mln = dev_factory.get_device(MID_CSP_MLN_DEVICE)
    assert csp_mln.memorizedDishVccMap == dish_cfg_input_str


def test_load_dish_cfg_command_invalid_json(
    tango_context, task_callback, json_factory
):
    """Test LoadDishCfg command rejected when invalid json provided"""
    logger.info("%s", tango_context)
    cm, _ = create_cm()
    cm.is_command_allowed("LoadDishCfg")
    dish_cfg_input_str = json_factory("command_load_dish_cfg")

    dish_cfg_input = json.loads(dish_cfg_input_str)
    dish_cfg_input.pop("tm_data_sources")

    result_code, message = cm.load_dish_cfg(
        json.dumps(dish_cfg_input), task_callback=task_callback
    )
    assert result_code == TaskStatus.REJECTED


def test_load_dish_cfg_command_invalid_file_name(
    tango_context, task_callback, json_factory
):
    """Test LoadDishCfg command rejected when invalid json provided"""
    logger.info("%s", tango_context)
    cm, _ = create_cm()
    cm.is_command_allowed("LoadDishCfg")
    dish_cfg_input_str = json_factory("command_load_dish_cfg_invalid")

    dish_cfg_input = json.loads(dish_cfg_input_str)

    result_code, message = cm.load_dish_cfg(
        json.dumps(dish_cfg_input), task_callback=task_callback
    )
    assert result_code == TaskStatus.REJECTED
