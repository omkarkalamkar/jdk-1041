import json

import pytest
import tango
from ska_tango_base.control_model import (
    ControlMode,
    HealthState,
    SimulationMode,
    TestMode,
)
from tango import DevState
from tango.test_utils import DeviceTestContext

from ska_tmc_centralnode import release
from ska_tmc_centralnode.central_node_mid import CentralNodeMid
from ska_tmc_centralnode.model.enum import ModesAvailability


@pytest.fixture
def central_node_device(request):
    """Create DeviceProxy for tests"""
    true_context = request.config.getoption("--true-context")
    if not true_context:
        with DeviceTestContext(CentralNodeMid) as proxy:
            yield proxy
    else:
        database = tango.Database()
        instance_list = database.get_device_exported_for_class(
            "CentralNodeMid"
        )
        for instance in instance_list.value_string:
            yield tango.DeviceProxy(instance)
            break


def test_attributes(central_node_device):
    assert central_node_device.HealthState == HealthState.OK
    assert central_node_device.State() == DevState.ON
    assert central_node_device.telescopehealthstate == HealthState.UNKNOWN
    central_node_device.loggingTargets = ["console::cout"]
    assert "console::cout" in central_node_device.loggingTargets
    central_node_device.testMode = TestMode.NONE
    assert central_node_device.testMode == TestMode.NONE
    central_node_device.simulationMode = SimulationMode.FALSE
    assert central_node_device.testMode == SimulationMode.FALSE
    assert central_node_device.telescopestate == DevState.UNKNOWN
    assert central_node_device.imaging == ModesAvailability.not_available
    assert central_node_device.pss == ModesAvailability.not_available
    assert central_node_device.pst == ModesAvailability.not_available
    assert central_node_device.vlbi == ModesAvailability.not_available
    central_node_device.controlMode = ControlMode.REMOTE
    assert central_node_device.controlMode == ControlMode.REMOTE
    assert central_node_device.desiredtelescopestate == DevState.ON
    assert central_node_device.commandinprogress == "None"
    assert central_node_device.cspmasterdevname == ""
    central_node_device.cspmasterdevname = "csp"
    assert central_node_device.cspmasterdevname == "csp"
    assert central_node_device.sdpmasterdevname == ""
    central_node_device.sdpmasterdevname = "sdp"
    assert central_node_device.sdpmasterdevname == "sdp"
    assert central_node_device.leafcspmasterdevname == ""
    central_node_device.leafcspmasterdevname = "leafcsp"
    assert central_node_device.leafcspmasterdevname == "leafcsp"
    assert central_node_device.leafsdpmasterdevname == ""
    central_node_device.leafsdpmasterdevname = "leafsdp"
    assert central_node_device.leafsdpmasterdevname == "leafsdp"
    assert central_node_device.tmopstate == DevState.UNKNOWN
    assert len(central_node_device.commandexecuted) == 1  # init
    assert "Init" in central_node_device.lastcommandexecuted  # init
    assert "OK" in central_node_device.lastcommandexecuted  # init
    assert len(central_node_device.subarraydevnames) == 0
    central_node_device.subarraydevnames = ["subarray1"]
    assert len(central_node_device.subarraydevnames) == 1
    assert len(central_node_device.cspsubarraydevnames) == 0
    central_node_device.cspsubarraydevnames = ["cspsubarray1"]
    assert len(central_node_device.cspsubarraydevnames) == 1
    assert len(central_node_device.sdpsubarraydevnames) == 0
    central_node_device.sdpsubarraydevnames = ["sdpsubarray1"]
    assert len(central_node_device.sdpsubarraydevnames) == 1
    assert len(central_node_device.dishdevnames) == 0
    central_node_device.dishdevnames = ["dish1"]
    assert len(central_node_device.dishdevnames) == 1
    central_node_device.tmleafdishdevnames = ["dish1"]
    assert len(central_node_device.tmleafdishdevnames) == 1
    json_model = json.loads(central_node_device.internalmodel)
    assert "telescope_state" in json_model
    assert "tmc_op_state" in json_model
    assert "telescope_health_state" in json_model
    assert "devices" in json_model
    json_model = json.loads(central_node_device.transformedinternalmodel)
    assert "telescope_state" in json_model
    assert "tmc_op_state" in json_model
    assert "telescope_health_state" in json_model
    assert "devices" not in json_model
    assert central_node_device.versionId == release.version
    assert central_node_device.buildState == (
        "{},{},{}".format(release.name, release.version, release.description)
    )
