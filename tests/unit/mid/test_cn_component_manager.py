"""Test cases file"""
from ska_tango_base.executor import TaskStatus
from ska_tmc_common.op_state_model import TMCOpStateModel

from ska_tmc_centralnode.manager.component_manager_mid import (
    CNComponentManagerMid,
)
from ska_tmc_centralnode.model.input import InputParameterMid
from tests.settings import logger


def test_telescope_on():
    """Test Telescope on"""
    op_state_model = TMCOpStateModel(logger)
    cm = CNComponentManagerMid(
        op_state_model, logger=logger, _input_parameter=InputParameterMid(None)
    )
    res_code, message = cm.telescope_on()
    assert res_code == TaskStatus.QUEUED
    assert message == "Task queued"


def test_telescope_off():
    """Test Telescope off"""
    op_state_model = TMCOpStateModel(logger)
    cm = CNComponentManagerMid(
        op_state_model, logger=logger, _input_parameter=InputParameterMid(None)
    )
    res_code, message = cm.telescope_off()
    assert res_code == TaskStatus.QUEUED
    assert message == "Task queued"
