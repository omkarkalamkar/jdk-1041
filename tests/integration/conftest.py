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
    MID_CENTRAL_NODE,
    SLEEP_TIME,
    TIMEOUT,
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


@pytest.fixture(scope="session", autouse=True)
def set_default_array_layout_url_attribute():
    """set DefaultArrayLayoutURL attribute"""
    logging.info("--- Session Setup ---")
    dev_factory = DevFactory()

    database = Database()
    mid_instance_list = database.get_device_exported_for_class(
        "MidTmcCentralNode"
    )
    logging.info("Mid instance_list: %s", mid_instance_list)

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
        logging.info("URL is: %s", url)
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
        logging.info("URL is: %s", url)
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
    yield
    logging.info("--- Session Teardown ---")
