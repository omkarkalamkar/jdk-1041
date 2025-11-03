"""Test case file"""

import json

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


@pytest.mark.test
def test_array_layout_default_read_mid(central_node_device):
    """Test to check DefaultarrayLayoutURL attribute value"""
    assert central_node_device.DefaultarrayLayoutURL == json.dumps(
        {
            "source_uris": [
                "gitlab://gitlab.com/ska-telescope/ska-telmodel-data?main#tmdata"
            ],
            "array_layout_path": "instrument/ska1_low/layout/low-layout.json",
        }
    )


@pytest.mark.test
def test_array_layout_default_write_mid(central_node_device):
    """Test to check DefaultarrayLayoutURL attribute write"""
    new_default_array_layout = {
        "source_uris": [
            "gitlab://gitlab.com/ska-telescope/ska-telmodel-data?main#tmdata"
        ],
        "array_layout_path": "instrument/ska1_low/layout/modified-low-layout.json",
    }
    central_node_device.DefaultarrayLayoutURL = json.dumps(
        new_default_array_layout
    )
    assert (
        json.loads(central_node_device.DefaultarrayLayoutURL)
        == new_default_array_layout
    )
