"""Conf test module for integration tests"""

# pylint: disable=redefined-outer-name
import json
import logging
import time

import pytest

from tests.settings import SLEEP_TIME, TIMEOUT, logger

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
