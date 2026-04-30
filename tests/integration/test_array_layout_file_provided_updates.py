"""Test cases for ON command"""

import logging

import pytest
from ska_control_model import HealthState
from ska_tmc_common.dev_factory import DevFactory

from ska_tmc_centralnode.utils.constants import (
    CENTRALNODE_LOW,
    CENTRALNODE_MID,
)
from tests.integration.conftest import ensure_checked_devices


# pylint:disable=c-extension-no-member
# this linting warning is suppressed cause its not able to recognise
# tango._tango.Devstate which is c-extension member
@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_array_layout_file_provided_updates(
    change_event_callbacks,
    set_mid_sdp_csp_mln_availability_for_aggregation,
    set_default_array_layout_url_attribute,
):
    """Test case to verify"""
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(CENTRALNODE_MID)
    assert central_node.HealthState == HealthState.OK
    ensure_checked_devices(central_node)

    logging.info(
        "CentralNode Low Initial arrayLayoutFileProvided: %s",
        central_node.arrayLayoutFileProvided,
    )
    logging.info(
        "central_node.DefaultArrayLayoutURL is: %s",
        central_node.DefaultArrayLayoutURL,
    )
    assert central_node.arrayLayoutFileProvided is True

    url = '{"source_uris":[""],"array_layout_path":""}'
    logging.info("URL is: %s", url)
    central_node.DefaultArrayLayoutURL = url
    assert central_node.arrayLayoutFileProvided is False

    url = (
        '{"source_uris":["gitlab://gitlab.com/ska-telescope/'
        + 'ska-telmodel-data?main#tmdata"],"array_layout_path":'
        + '"instrument/ska1_mid/layout/mid-layout.json"}'
    )
    logging.info("URL is: %s", url)
    central_node.DefaultArrayLayoutURL = url
    assert central_node.arrayLayoutFileProvided is True


@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_on_command_low(
    change_event_callbacks,
    set_low_devices_availability_for_aggregation,
    set_default_array_layout_url_attribute,
):
    """Test cases for ON command for low"""
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(CENTRALNODE_LOW)
    assert central_node.HealthState == HealthState.OK
    ensure_checked_devices(central_node)

    logging.info(
        "CentralNode Low Initial arrayLayoutFileProvided: %s",
        central_node.arrayLayoutFileProvided,
    )
    assert central_node.arrayLayoutFileProvided is True

    url = '{"source_uris":[""],"array_layout_path":""}'
    logging.info("URL is: %s", url)
    central_node.DefaultArrayLayoutURL = url
    assert central_node.arrayLayoutFileProvided is False

    url = (
        '{"source_uris":["gitlab://gitlab.com/ska-telescope/'
        + 'ska-telmodel-data?main#tmdata"],"array_layout_path":'
        + '"instrument/ska1_low/layout/low-layout.json"}'
    )
    logging.info("URL is: %s", url)
    central_node.DefaultArrayLayoutURL = url
    assert central_node.arrayLayoutFileProvided is True
