"""Conf test module for integration tests"""

# pylint: disable=redefined-outer-name
import json
import logging
import time

import pytest
from ska_tmc_common.dev_factory import DevFactory
from tango import Database

from tests.settings import (
    LOW_CENTRAL_NODE,
    LOW_SUBARRAY2_DEVICE,
    LOW_SUBARRAY_DEVICE,
    MID_CENTRAL_NODE,
    MID_SUBARRAY2_DEVICE,
    MID_SUBARRAY_DEVICE,
    SLEEP_TIME,
    TIMEOUT,
    check_subarray_availability,
    logger,
)

pytest.event_arrived = False


def checked_devices(json_model: dict) -> int:
    """Checked devices for availability"""
    result = 0
    for dev in json_model["devices"]:
        if dev["unresponsive"] == "False":
            result += 1
    return result


def ensure_checked_devices(central_node):
    """Ensures checked devices"""
    json_model = json.loads(central_node.internalModel)
    start_time = time.time()
    checked_devs = checked_devices(json_model)
    while checked_devs != len(json_model["devices"]):
        new_checked_devs = checked_devices(json_model)
        if checked_devs != new_checked_devs:
            checked_devs = new_checked_devs
            logger.debug("checked devices: %s", checked_devs)
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            logger.debug(central_node.internalModel)
            pytest.fail("Timeout occurred while executing the test")
        json_model = json.loads(central_node.internalModel)
    logger.debug("central_node.internalModel: %s", central_node.internalModel)


def assert_event_arrived():
    """Assert whether event arrived"""
    start_time = time.time()
    while not pytest.event_arrived:
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")

    assert pytest.event_arrived


@pytest.fixture(scope="session")
def set_default_array_layout_url_attribute():
    """set DefaultArrayLayoutURL attribute"""
    dev_factory = DevFactory()
    database = Database()
    mid_instance_list = database.get_device_exported_for_class(
        "MidTmcCentralNode"
    )

    if mid_instance_list.value_string:
        central_node = dev_factory.get_device(MID_CENTRAL_NODE)
        logging.info(
            "CentralNode Mid Initial arrayLayoutFileProvided: %s",
            central_node.arrayLayoutFileProvided,
        )
        assert central_node.arrayLayoutFileProvided is False
        logging.info(
            "CentralNode Mid Initial DefaultArrayLayoutURL: %s",
            central_node.DefaultArrayLayoutURL,
        )

        url = (
            '{"source_uris":["gitlab://gitlab.com/ska-telescope/'
            + 'ska-telmodel-data?main#tmdata"],"array_layout_path":'
            + '"instrument/ska1_mid/layout/mid-layout.json"}'
        )
        central_node.DefaultArrayLayoutURL = url
        logging.info(
            "CentralNode Mid DefaultArrayLayoutURL: %s",
            central_node.DefaultArrayLayoutURL,
        )
        logging.info(
            "CentralNode Mid arrayLayoutFileProvided: %s",
            central_node.arrayLayoutFileProvided,
        )
        assert central_node.arrayLayoutFileProvided is True
    else:
        central_node = dev_factory.get_device(LOW_CENTRAL_NODE)
        logging.info(
            "CentralNode Low Initial arrayLayoutFileProvided: %s",
            central_node.arrayLayoutFileProvided,
        )
        assert central_node.arrayLayoutFileProvided is False
        logging.info(
            "CentralNode Low Initial DefaultArrayLayoutURL: %s",
            central_node.DefaultArrayLayoutURL,
        )
        url = (
            '{"source_uris":["gitlab://gitlab.com/ska-telescope/'
            + 'ska-telmodel-data?main#tmdata"],"array_layout_path":'
            + '"instrument/ska1_low/layout/low-layout.json"}'
        )
        central_node.DefaultArrayLayoutURL = url
        logging.info(
            "CentralNode Low DefaultArrayLayoutURL: %s",
            central_node.DefaultArrayLayoutURL,
        )
        logging.info(
            "CentralNode Low Initial arrayLayoutFileProvided: %s",
            central_node.arrayLayoutFileProvided,
        )
        assert central_node.arrayLayoutFileProvided is True


def get_cn_sn(central_node_name: str, subarray_count=1) -> tuple:
    """Provides the Central and subarray node device proxies"""
    subarray_node_name = LOW_SUBARRAY_DEVICE
    subarray_node2_name = LOW_SUBARRAY2_DEVICE
    subarray_node2 = None
    if "mid-tmc" in central_node_name:
        subarray_node_name = MID_SUBARRAY_DEVICE
        subarray_node2_name = MID_SUBARRAY2_DEVICE
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_name)
    subarray_node = dev_factory.get_device(subarray_node_name)

    ensure_checked_devices(central_node)
    subarray_node.SetisSubarrayAvailable(True)
    check_subarray_availability(central_node, subarray_node_name, True)
    if subarray_count == 2:
        subarray_node2 = dev_factory.get_device(subarray_node2_name)
        subarray_node2.SetisSubarrayAvailable(True)
        check_subarray_availability(central_node, subarray_node2_name, True)
    return central_node, subarray_node, subarray_node2
