import time

import pytest
from ska_tmc_common.device_info import SubArrayDeviceInfo

from ska_tmc_centralnode.model.input import InputParameterLow
from tests.settings import count_faulty_devices, create_cm, logger


@pytest.mark.low
def test_all_working(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm(input_parameter=InputParameterLow(None))
    num_faulty = count_faulty_devices(cm)
    assert num_faulty == 0

    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", num_faulty, elapsed_time)
    for devInfo in cm.devices:
        assert not devInfo.unresponsive
        if "subarray" in devInfo.dev_name.lower():
            assert isinstance(devInfo, SubArrayDeviceInfo)
