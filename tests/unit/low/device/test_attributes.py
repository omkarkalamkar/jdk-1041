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
from ska_tmc_centralnode.central_node_low import CentralNodeLow


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


@pytest.mark.cn_cm
def test_attributes(central_node_device):
    assert central_node_device.HealthState == HealthState.UNKNOWN
    assert central_node_device.State() == DevState.UNKNOWN
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
    assert central_node_device.desiredTelescopeState == DevState.ON
    assert central_node_device.commandInProgress == "None"
    assert central_node_device.mccsMasterLeafNodeName == ""
    central_node_device.mccsMasterLeafNodeName = "mccs_master_leaf"
    assert central_node_device.mccsMasterLeafNodeName == "mccs_master_leaf"
    assert central_node_device.mccsSubarrayLeafNodeName == ""
    central_node_device.mccsSubarrayLeafNodeName = "mccs_subarray_leaf"
    assert central_node_device.mccsSubarrayLeafNodeName == "mccs_subarray_leaf"
    assert central_node_device.mccsMasterNodeName == ""
    central_node_device.mccsMasterNodeName = "mccs"
    assert central_node_device.mccsMasterNodeName == "mccs"

    assert central_node_device.tmOpstate == DevState.UNKNOWN
    assert len(central_node_device.commandExecuted) == 1  # init
    assert "Init" in central_node_device.lastCommandExecuted  # init
    assert "OK" in central_node_device.lastCommandExecuted  # init
    assert len(central_node_device.subarrayDevNames) == 0
    central_node_device.subarrayDevNames = ["subarray1"]
    assert len(central_node_device.subarrayDevNames) == 1
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
