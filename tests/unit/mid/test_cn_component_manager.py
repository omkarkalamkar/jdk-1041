"""Test cases file"""

from unittest.mock import Mock

from ska_control_model import TaskStatus
from ska_tmc_common.op_state_model import TMCOpStateModel

from ska_tmc_centralnode.manager.component_manager_mid import (
    CNComponentManagerMid,
)
from ska_tmc_centralnode.model.input import InputParameterMid
from tests.settings import dish_vcc_process_callback, logger


def mock_callback(*args, **kwargs):
    """Devices to mock_callback"""


def test_telescope_on():
    """Test Telescope on"""
    op_state_model = TMCOpStateModel(logger)

    default_array_layout_url = {
        "source_uris": [
            "gitlab://gitlab.com/ska-telescope/"
            "ska-telmodel-data?main#tmdata"
        ],
        "array_layout_path": "instrument/ska1_mid/layout/mid-layout.json",
    }

    mock_array_layout_callback = Mock()

    cm = CNComponentManagerMid(
        op_state_model,
        _input_parameter=InputParameterMid(None),
        logger=logger,
        _dish_vcc_command_status_callback=dish_vcc_process_callback,
        _update_device_callback=mock_callback,
        _update_telescope_state_callback=mock_callback,
        _update_telescope_health_state_callback=mock_callback,
        _update_tmc_op_state_callback=mock_callback,
        _update_imaging_callback=mock_callback,
        _telescope_availability_callback=mock_callback,
        array_layout_url_callback=mock_array_layout_callback,
        default_array_layout_url_callback=mock_array_layout_callback,
        _update_dishvccconfig_callback=mock_callback,
        _dishvccvalidation_callback=mock_callback,
        default_array_layout_url=default_array_layout_url,
    )

    res_code, message = cm.telescope_on()
    assert res_code == TaskStatus.IN_PROGRESS
    assert message == "Task queued"


def test_telescope_off():
    """Test Telescope off"""
    op_state_model = TMCOpStateModel(logger)

    default_array_layout_url = {
        "source_uris": [
            "gitlab://gitlab.com/ska-telescope/"
            "ska-telmodel-data?main#tmdata"
        ],
        "array_layout_path": "instrument/ska1_mid/layout/mid-layout.json",
    }

    mock_array_layout_callback = Mock()

    cm = CNComponentManagerMid(
        op_state_model,
        _input_parameter=InputParameterMid(None),
        logger=logger,
        _dish_vcc_command_status_callback=dish_vcc_process_callback,
        _update_device_callback=mock_callback,
        _update_telescope_state_callback=mock_callback,
        _update_telescope_health_state_callback=mock_callback,
        _update_tmc_op_state_callback=mock_callback,
        _update_imaging_callback=mock_callback,
        _telescope_availability_callback=mock_callback,
        array_layout_url_callback=mock_array_layout_callback,
        default_array_layout_url_callback=mock_array_layout_callback,
        _update_dishvccconfig_callback=mock_callback,
        _dishvccvalidation_callback=mock_callback,
        default_array_layout_url=default_array_layout_url,
    )

    res_code, message = cm.telescope_off()
    assert res_code == TaskStatus.IN_PROGRESS
    assert message == "Task queued"
