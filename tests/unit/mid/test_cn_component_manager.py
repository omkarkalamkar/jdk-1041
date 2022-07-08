import pytest
from ska_tango_base.executor import TaskStatus

from ska_tmc_centralnode.manager.component_manager import CNComponentManager
from ska_tmc_centralnode.model.input import InputParameterMid
from tests.settings import logger


@pytest.mark.cn_cm
def test_telescope_on():
    cm = CNComponentManager(
        logger=logger, _input_parameter=InputParameterMid(None)
    )
    res_code, message = cm.telescope_on()
    assert res_code == TaskStatus.QUEUED
    assert message == "Task queued"
