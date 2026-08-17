"""Test cases for ON command"""

import pytest
from ska_control_model import HealthState
from ska_tmc_common.dev_factory import DevFactory

from ska_tmc_centralnode.utils.constants import (
    CENTRALNODE_LOW,
    CENTRALNODE_MID,
)
from tests.integration.conftest import ensure_checked_devices
from tests.settings import set_low_devices_availability


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.usefixtures(
    "set_mid_sdp_csp_mln_availability_for_aggregation",
    "set_default_array_layout_url_attribute",
)
def test_array_layout_file_provided_updates():
    """Test case to verify"""
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(CENTRALNODE_MID)
    assert central_node.HealthState == HealthState.OK
    ensure_checked_devices(central_node)

    assert central_node.arrayLayoutFileProvided is True

    url = '{"source_uris":[""],"array_layout_path":""}'
    central_node.DefaultArrayLayoutURL = url
    assert central_node.arrayLayoutFileProvided is False

    url = (
        '{"source_uris":["gitlab://gitlab.com/ska-telescope/'
        + 'ska-telmodel-data?main#tmdata"],"array_layout_path":'
        + '"instrument/ska1_mid/layout/mid-layout.json"}'
    )
    central_node.DefaultArrayLayoutURL = url
    assert central_node.arrayLayoutFileProvided is True


@pytest.mark.post_deployment
@pytest.mark.SKA_low
@pytest.mark.usefixtures("set_default_array_layout_url_attribute")
def test_on_command_low():
    """Test cases for ON command for low"""
    set_low_devices_availability()
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(CENTRALNODE_LOW)
    assert central_node.HealthState == HealthState.OK
    ensure_checked_devices(central_node)

    assert central_node.arrayLayoutFileProvided is True

    url = '{"source_uris":[""],"array_layout_path":""}'
    central_node.DefaultArrayLayoutURL = url
    assert central_node.arrayLayoutFileProvided is False

    url = (
        '{"source_uris":["gitlab://gitlab.com/ska-telescope/'
        + 'ska-telmodel-data?main#tmdata"],"array_layout_path":'
        + '"instrument/ska1_low/layout/low-layout.json"}'
    )
    central_node.DefaultArrayLayoutURL = url
    assert central_node.arrayLayoutFileProvided is True
