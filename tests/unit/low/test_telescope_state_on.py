import pytest
import tango
from ska_tmc_common.dev_factory import DevFactory

from ska_tmc_centralnode.model.input import InputParameterLow
from tests.settings import (
    create_cm_no_faulty_devices,
    ensure_telescope_state,
    set_devices_state,
)


def set_devices_on(cm, devFactory, expected_elapsed_time):
    set_devices_state(
        devices=[
            "low-mccs/control/control",
        ],
        devFactory=devFactory,
        state=tango.DevState.ON,
        cm=cm,
        expected_elapsed_time=expected_elapsed_time,
    )
    ensure_telescope_state(cm, tango.DevState.ON, expected_elapsed_time=12)


@pytest.mark.low
def test_telescope_state_on(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, InputParameterLow(None)
    )
    set_devices_on(cm, devFactory, 15)
    assert cm.component.telescope_state == tango.DevState.ON
