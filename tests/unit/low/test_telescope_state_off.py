import pytest
import tango
from ska_tmc_common.dev_factory import DevFactory

from ska_tmc_centralnode.model.input import InputParameterLow
from tests.settings import (
    create_cm_no_faulty_devices,
    ensure_telescope_state,
    set_device_state,
)


@pytest.mark.low
def test_telescope_state_off(tango_context):
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, InputParameterLow(None)
    )
    set_device_state(
        "low-mccs/control/control",
        devFactory=DevFactory(),
        state=tango.DevState.OFF,
    )
    ensure_telescope_state(cm, tango.DevState.OFF, expected_elapsed_time=15)
    assert cm.component.telescope_state == tango.DevState.OFF
