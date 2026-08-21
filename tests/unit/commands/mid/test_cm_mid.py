"""Module to test MID component manager functioanlity."""

import json
from unittest import mock

from ska_control_model import ResultCode
from tango import DevState

from ska_tmc_centralnode.utils.constants import (
    DISH_VCC_CONFIG_INTERFACE_VERSION,
)
from tests.settings import (
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
