"""Test cases for testing commands"""

import pytest
import tango
from tango.test_utils import DeviceTestContext

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
def test_commands(central_node_device):
    """Test Command for low telescope"""
    try:
        central_node_device.TelescopeOn()
        central_node_device.TelescopeOff()
        central_node_device.off()

    except Exception as ex:
        assert "CommandNotAllowed" in str(ex)

    with pytest.raises(Exception):
        central_node_device.StartUpTelescope()
        central_node_device.StandByTelescope()
        central_node_device.Standby()
        central_node_device.TelescopeStandby()
