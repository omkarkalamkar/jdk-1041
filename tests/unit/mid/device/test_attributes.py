import json

import pytest
import tango
from ska_control_model import HealthState
from ska_tango_base.control_model import ControlMode, SimulationMode, TestMode
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
    assert central_node_device.State() in [
        tango._tango.DevState.UNKNOWN,
        tango._tango.DevState.ON,
    ]
    assert central_node_device.HealthState == HealthState.OK
    assert central_node_device.telescopeHealthstate == HealthState.UNKNOWN
    central_node_device.loggingTargets = ["console::cout"]
    assert "console::cout" in central_node_device.loggingTargets
    central_node_device.testMode = TestMode.NONE
    assert central_node_device.testMode == TestMode.NONE
    central_node_device.simulationMode = SimulationMode.FALSE
    assert central_node_device.testMode == SimulationMode.FALSE
    assert central_node_device.telescopeState == DevState.UNKNOWN
    assert central_node_device.imaging == ModesAvailability.not_available
    assert central_node_device.pss == ModesAvailability.not_available
    assert central_node_device.pst == ModesAvailability.not_available
    assert central_node_device.vlbi == ModesAvailability.not_available
    central_node_device.controlMode = ControlMode.REMOTE
    assert central_node_device.controlMode == ControlMode.REMOTE
    assert central_node_device.desiredTelescopeState == DevState.ON
    assert central_node_device.cspMasterDevName == ""
    central_node_device.cspMasterDevName = "csp"
    assert central_node_device.cspMasterDevName == "csp"
    assert central_node_device.sdpMasterDevName == ""
    central_node_device.sdpMasterDevName = "sdp"
    assert central_node_device.sdpMasterDevName == "sdp"
    assert central_node_device.CspMasterLeafNodeDevName == ""
    central_node_device.CspMasterLeafNodeDevName = "leafcsp"
    assert central_node_device.CspMasterLeafNodeDevName == "leafcsp"
    assert central_node_device.SdpMasterLeafNodeDevName == ""
    central_node_device.SdpMasterLeafNodeDevName = "leafsdp"
    assert central_node_device.SdpMasterLeafNodeDevName == "leafsdp"
    assert central_node_device.tmOpState == DevState.UNKNOWN
    assert len(central_node_device.subarrayDevNames) == 0
    central_node_device.subarrayDevNames = ["subarray1"]
    assert len(central_node_device.subarrayDevNames) == 1
    assert len(central_node_device.dishDevNames) == 0
    central_node_device.dishDevNames = ["dish1"]
    assert len(central_node_device.dishDevNames) == 1
    central_node_device.dishLeafNodeDevNames = ["dish1"]
    assert len(central_node_device.dishLeafNodeDevNames) == 1
    json_model = json.loads(central_node_device.internalModel)
    assert "telescope_state" in json_model
    assert "tmc_op_state" in json_model
    assert "telescope_health_state" in json_model
    assert "devices" in json_model
    json_model = json.loads(central_node_device.transformedInternalModel)
    assert "telescope_state" in json_model
    assert "tmc_op_state" in json_model
    assert "telescope_health_state" in json_model
    assert "devices" not in json_model
    assert central_node_device.versionId == release.version
    assert central_node_device.buildState == (
        "{},{},{}".format(release.name, release.version, release.description)
    )
