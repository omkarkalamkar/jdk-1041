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

from ska_tmc_centralnode_mid import release
from ska_tmc_centralnode_mid.central_node_low import CentralNodeLow
from ska_tmc_centralnode_mid.model.enum import ModesAvailability


@pytest.fixture
def central_node_device(request):
    """Create DeviceProxy for tests"""
    true_context = request.config.getoption("--true-context")
    if not true_context:
        with DeviceTestContext(CentralNodeLow) as proxy:
            yield proxy
    else:
        database = tango.Database()
        instance_list = database.get_device_exported_for_class(
            "CentralNodeLow"
        )
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
    central_node_device.controlMode = ControlMode.REMOTE
    assert central_node_device.controlMode == ControlMode.REMOTE
    assert central_node_device.subarray1HealthState == HealthState.UNKNOWN
    assert central_node_device.subarray2HealthState == HealthState.UNKNOWN
    assert central_node_device.subarray3HealthState == HealthState.UNKNOWN
    assert central_node_device.desiredTelescopeState == DevState.ON
    assert central_node_device.commandInProgress == "None"
    assert central_node_device.MCCSMasterLeafNodeName == ""
    central_node_device.MCCSMasterLeafNodeName = "mccs"
    assert central_node_device.MCCSMasterLeafNodeName == "mccs"
    assert central_node_device.TMOpState == DevState.UNKNOWN
    assert len(central_node_device.CommandExecuted) == 1  # init
    assert "Init" in central_node_device.LastCommandExecuted  # init
    assert "OK" in central_node_device.LastCommandExecuted  # init
    assert len(central_node_device.SubarrayDevNames) == 0
    central_node_device.SubarrayDevNames = ["subarray1"]
    assert len(central_node_device.SubarrayDevNames) == 1
    json_model = json.loads(central_node_device.InternalModel)
    assert "telescope_state" in json_model
    assert "tmc_op_state" in json_model
    assert "telescope_health_state" in json_model
    assert "devices" in json_model
    json_model = json.loads(central_node_device.TransformedInternalModel)
    assert "telescope_state" in json_model
    assert "tmc_op_state" in json_model
    assert "telescope_health_state" in json_model
    assert "devices" not in json_model
    assert central_node_device.versionId == release.version
    assert central_node_device.buildState == (
        "{},{},{}".format(release.name, release.version, release.description)
    )
