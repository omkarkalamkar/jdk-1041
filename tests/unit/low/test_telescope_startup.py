import pytest
import tango
from ska_tango_base.control_model import HealthState

from ska_tmc_centralnode.model.input import InputParameterLow
from tests.settings import create_cm_no_faulty_devices


@pytest.mark.SKA_low
def test_aggregation_default(tango_context):
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, InputParameterLow(None)
    )
    assert cm.component.telescope_state == tango.DevState.UNKNOWN
    assert cm.component.tmc_op_state == tango.DevState.UNKNOWN
    assert cm.component.telescope_health_state in [
        HealthState.UNKNOWN,
        HealthState.OK,
    ]
