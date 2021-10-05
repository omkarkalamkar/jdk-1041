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

from ska_tmc_centralnode_mid.central_node import CentralNode
from ska_tmc_centralnode_mid.model.enum import ModesAvailability


@pytest.fixture
def central_node_device(request):
    """Create DeviceProxy for tests"""
    true_context = request.config.getoption("--true-context")
    if not true_context:
        with DeviceTestContext(CentralNode) as proxy:
            yield proxy
    else:
        database = tango.Database()
        instance_list = database.get_device_exported_for_class("CentralNode")
        for instance in instance_list.value_string:
            yield tango.DeviceProxy(instance)
            break


def test_attributes(central_node_device):
    assert central_node_device.HealthState == HealthState.OK
    assert central_node_device.State() == DevState.ON
    assert central_node_device.telescopeHealthState == HealthState.UNKNOWN
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
    assert central_node_device.subarray1HealthState == HealthState.UNKNOWN
    assert central_node_device.subarray2HealthState == HealthState.UNKNOWN
    assert central_node_device.subarray3HealthState == HealthState.UNKNOWN
    assert central_node_device.desiredTelescopeState == DevState.ON
    assert central_node_device.commandInProgress == ""
    assert central_node_device.CspMasterDevName == ""
    central_node_device.CspMasterDevName = "csp"
    assert central_node_device.CspMasterDevName == "csp"
    assert central_node_device.SdpMasterDevName == ""
    central_node_device.SdpMasterDevName = "sdp"
    assert central_node_device.SdpMasterDevName == "sdp"
    assert central_node_device.LeafCspMasterDevName == ""
    central_node_device.LeafCspMasterDevName = "leafcsp"
    assert central_node_device.LeafCspMasterDevName == "leafcsp"
    assert central_node_device.LeafSdpMasterDevName == ""
    central_node_device.LeafSdpMasterDevName = "leafsdp"
    assert central_node_device.LeafSdpMasterDevName == "leafsdp"
    assert central_node_device.TMOpState == DevState.UNKNOWN
    assert len(central_node_device.CommandExecuted) == 1  # init
    assert len(central_node_device.SubarrayDevNames) == 0
    central_node_device.SubarrayDevNames = ["subarray1"]
    assert len(central_node_device.SubarrayDevNames) == 1
    assert len(central_node_device.CspSubarrayDevNames) == 0
    central_node_device.CspSubarrayDevNames = ["cspsubarray1"]
    assert len(central_node_device.CspSubarrayDevNames) == 1
    assert len(central_node_device.SdpSubarrayDevNames) == 0
    central_node_device.SdpSubarrayDevNames = ["sdpsubarray1"]
    assert len(central_node_device.SdpSubarrayDevNames) == 1
    assert len(central_node_device.DishDevNames) == 0
    central_node_device.DishDevNames = ["dish1"]
    assert len(central_node_device.DishDevNames) == 1
    json_model = json.loads(central_node_device.InternalModel)
    assert "telescope_state" in json_model
    assert "tmc_op_state" in json_model
    assert "telescope_health_state" in json_model
    assert "devices" in json_model
