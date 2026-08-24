"""Module to test MID component manager functioanlity."""

import json
from unittest import mock

from ska_control_model import ResultCode, TaskStatus
from tango import DevState

from ska_tmc_centralnode.utils.constants import (
    DISH_VCC_CONFIG_INTERFACE_VERSION,
)
from tests.settings import (
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    MID_CENTRAL_NODE,
    MID_CSP_MLN_DEVICE,
    create_cm,
)


def test_get_dev_names():
    cm, _ = create_cm()
    assert cm.get_dish_device_names() == [DISH_MASTER_DEVICE]


def test_dish_vcc_validation_status():
    cm, _ = create_cm()
    csp_master_unavailable = "CSP Master device is unavailable"
    cm._dish_vcc_validation_status = json.dumps(
        {MID_CSP_MLN_DEVICE: csp_master_unavailable}
    )
    status = {
        "dish": "ALL DISH OK",
        MID_CSP_MLN_DEVICE: csp_master_unavailable,
    }
    cm.dish_vcc_validation_status = status
    assert not cm.is_dish_vcc_config_set
    assert cm._dish_vcc_validation_status == json.dumps(status)
    previous_status = status
    status = {MID_CENTRAL_NODE: csp_master_unavailable}
    cm.dish_vcc_validation_status = status
    status = {**previous_status, **status}
    assert cm._dish_vcc_validation_status == json.dumps(status)
    cm._dish_vcc_validation_status = json.dumps(
        {MID_CSP_MLN_DEVICE: csp_master_unavailable}
    )
    status = {"ska100": "k-value not set"}
    cm.dish_vcc_validation_status = status
    assert cm._dish_vcc_validation_status == json.dumps(
        {
            **status,
            MID_CSP_MLN_DEVICE: csp_master_unavailable,
        }
    )


def test_is_csp_master_ready(caplog):
    cm, _ = create_cm()
    cm.config.dish_config.init_timeout = 2
    result_code = cm.is_csp_mln_csp_master_ready()
    assert result_code == ResultCode.FAILED
    csp_mock = mock.Mock(state=DevState.ON)
    cm.adapter_factory = mock.Mock()
    cm.adapter_factory.get_or_create_adapter.return_value = csp_mock
    result_code = cm.is_csp_mln_csp_master_ready()
    assert result_code == ResultCode.NOT_ALLOWED
    csp_mock.state = DevState.OFF
    result_code = cm.is_csp_mln_csp_master_ready()
    assert result_code == ResultCode.OK
    cm.adapter_factory.get_or_create_adapter.side_effect = Exception("error")
    result_code = cm.is_csp_mln_csp_master_ready()
    assert result_code == ResultCode.FAILED
    assert "error" in caplog.records[-1].message


def test_default_vcc_config_param():
    cm, _ = create_cm()
    param = cm.get_default_dish_vcc_config_params()
    assert param == {
        "interface": DISH_VCC_CONFIG_INTERFACE_VERSION,
        "tm_data_sources": [""],
        "tm_data_filepath": "",
    }


def test_check_if_csp_all_ready(tango_context):
    cm, _ = create_cm()
    cm.config.dish_config.init_timeout = 10
    cm.input_parameter.dish_leaf_node_dev_names = [
        DISH_LEAF_NODE_DEVICE,
        DISH_LEAF_NODE_DEVICE,
    ]
    is_ready = cm.check_if_csp_all_dish_ready()
    assert is_ready
    dish_mock = mock.Mock()
    dish_mock.proxy.kValueValidationResult = "1"
    cm.adapter_factory = mock.Mock()
    cm.adapter_factory.get_or_create_adapter.return_value = dish_mock
    is_ready = cm.check_if_csp_all_dish_ready()
    assert not is_ready


def test_update_k_value_aggregator():
    cm, _ = create_cm()
    cm.update_kval_aggregator("SKA001", "")
    aggregator = cm.dish_kvalue_validation_aggregator
    assert aggregator.dln_kvalue_validation_results == {"ska001": ""}


def test_append_dish_dev_names():
    cm, _ = create_cm()
    cm.append_dish_dev_names("ska001")
    assert cm.dev_names_for_load_dish_cfg == ["ska001"]


def test_load_dish_cfg_rejection():
    cm, _ = create_cm()
    cm.is_csp_mln_csp_master_ready = mock.Mock()
    cm.is_csp_mln_csp_master_ready.return_value = ResultCode.NOT_ALLOWED
    task_cb = mock.Mock()
    cm.load_dish_cfg("", task_cb, mock.Mock())
    assert not cm.is_dish_vcc_config_set
    err_msg = (
        "LoadDishCfg command is allowed in" " CSP Master DevState.OFF only."
    )
    task_cb.assert_called_once_with(
        status=TaskStatus.REJECTED,
        result=(ResultCode.NOT_ALLOWED, err_msg),
    )

    cm.is_csp_mln_csp_master_ready.return_value = ResultCode.FAILED
    cm.load_dish_cfg("", task_cb, mock.Mock())
    err_msg = (
        "CSP master or CSP MLN is not available for" " loaddishcfg execution"
    )
    assert not cm.is_dish_vcc_config_set
    task_cb.assert_called_with(
        status=TaskStatus.REJECTED,
        result=(ResultCode.NOT_ALLOWED, err_msg),
    )
    cm.is_csp_mln_csp_master_ready.return_value = ResultCode.OK
    cm.load_dish_cfg("", task_cb, mock.Mock())
    kwargs = task_cb.call_args_list[-1].kwargs
    assert kwargs.get("status") == TaskStatus.REJECTED
    assert kwargs.get("result")[0] == ResultCode.NOT_ALLOWED
    assert "The JSON string is malformed." in kwargs.get("result")[1]


def test_stow_mode_error():
    cm, _ = create_cm()
    task_cb = mock.Mock()
    cm.set_stow_mode("{}", task_cb, mock.Mock())
    kwargs = task_cb.call_args_list[-1].kwargs
    assert kwargs.get("status") == TaskStatus.REJECTED
    assert kwargs.get("result")[0] == ResultCode.NOT_ALLOWED
    assert (
        "Invalid input: Expected a list of dish IDs" in kwargs.get("result")[1]
    )


def test_check_invoke_gpm_not_called():
    cm, _ = create_cm()
    cm.is_gpm_init = False
    cm.config.gpm_config.invoke_command_callback = mock.Mock()
    cm._check_init_and_invoke_gpm()
    cm.config.gpm_config.invoke_command_callback.assert_not_called()
    cm.is_gpm_init = True
    cm.config.gpm_config.invoke_command_callback = None
    cm._check_init_and_invoke_gpm()
    cm.is_gpm_init = True


def test_assign_k_value_failed(json_factory):
    cm, _ = create_cm()
    cm.dish_vcc_validation_status = {"ska001": "k-value not set"}

    assign_str = json_factory("command_AssignResources")
    task_cb = mock.Mock()
    cm.assign_resources(assign_str, task_cb, mock.Mock())
    kwargs = task_cb.call_args_list[-1].kwargs
    assert kwargs.get("status") == TaskStatus.REJECTED
    assert kwargs.get("result")[0] == ResultCode.NOT_ALLOWED
    result = kwargs.get("result")[1]
    assert "Can't assign receptors with k-value issues:" in result


def test_validate_dish_id():
    cm, _ = create_cm()
    is_valid, msg = cm.validate_dish_ids(["asf123"])
    assert not is_valid
    assert "Invalid Dish id ASF123 provided in Json" in msg
    cm.config.mkt_extension_id = "ASF"
    is_valid, msg = cm.validate_dish_ids(["asf123"])
    assert is_valid
    assert "" == msg
