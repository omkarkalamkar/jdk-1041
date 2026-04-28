"""Test case file"""

import json

import pytest
import tango
from ska_control_model import HealthState
from ska_tango_base.control_model import ControlMode, SimulationMode, TestMode
from tango import DevState
from tango.test_utils import DeviceTestContext

from ska_tmc_centralnode import release
from ska_tmc_centralnode.central_node_low import LowTmcCentralNode


@pytest.fixture
def central_node_device(request):
    """Create DeviceProxy for tests"""
    true_context = request.config.getoption("--true-context")
    if not true_context:
        with DeviceTestContext(LowTmcCentralNode, timeout=50) as proxy:
            yield proxy
    else:
        database = tango.Database()
        instance_list = database.get_device_exported_for_class(
            "LowTmcCentralNode"
        )
        for instance in instance_list.value_string:
            yield tango.DeviceProxy(instance)
            break


@pytest.mark.SKA_low
def test_attributes(central_node_device):
    """Test attributes for low"""
    assert central_node_device.State() in [DevState.UNKNOWN, DevState.ON]
    assert central_node_device.HealthState == HealthState.OK
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
    assert central_node_device.tmOpstate == DevState.UNKNOWN
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
    assert central_node_device.arrayLayoutFileProvided is False
    print(
        "central_node_device.DefaultArrayLayoutURL",
        json.loads(central_node_device.DefaultArrayLayoutURL),
    )
    assert json.loads(central_node_device.DefaultArrayLayoutURL) == {
        "source_uris": [None],
        "array_layout_path": None,
    }


@pytest.mark.SKA_low
def test_assign_resources_schema_version_attribute(central_node_device):
    """Test assignResourcesSchemaVersion attribute read and write"""
    # Test read
    initial_version = central_node_device.assignResourcesSchemaVersion
    assert isinstance(initial_version, str)

    # Test write
    test_version = "2.5"
    central_node_device.assignResourcesSchemaVersion = test_version
    assert central_node_device.assignResourcesSchemaVersion == test_version


@pytest.mark.SKA_low
def test_release_resources_schema_version_attribute(central_node_device):
    """Test releaseResourcesSchemaVersion attribute read and write"""
    # Test read
    initial_version = central_node_device.releaseResourcesSchemaVersion
    assert isinstance(initial_version, str)

    # Test write
    test_version = "3.0"
    central_node_device.releaseResourcesSchemaVersion = test_version
    assert central_node_device.releaseResourcesSchemaVersion == test_version
