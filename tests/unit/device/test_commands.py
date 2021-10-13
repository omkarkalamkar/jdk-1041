import pytest
import tango
from tango.test_utils import DeviceTestContext

from ska_tmc_centralnode_mid.central_node import CentralNode
from ska_tmc_centralnode_mid.exceptions import CommandNotAllowed


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


def test_commands(central_node_device):
    with pytest.raises(CommandNotAllowed):
        central_node_device.On()
        central_node_device.TelescopeOn()
        central_node_device.Off()
        central_node_device.TelescopeOff()
        central_node_device.StartUpTelescope()
        central_node_device.StandByTelescope()
        central_node_device.Standby()
        central_node_device.TelescopeStandby()
