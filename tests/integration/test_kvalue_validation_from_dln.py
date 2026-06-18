"""Test case for kvalue validation from dish leaf node"""

import json

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from tango import DeviceProxy

from ska_tmc_centralnode.utils.constants import (
    CENTRALNODE_MID,
    DISH_LEAF_NODE_1,
    DISH_LEAF_NODE_36,
    DISH_LEAF_NODE_63,
    DISH_LEAF_NODE_77,
    DISH_LEAF_NODE_099,
    DISH_LEAF_NODE_100,
    DISH_LEAF_NODE_500,
    DISH_LEAF_NODE_999,
    DISH_LEAF_NODE_MKT,
)
from tests.common_utils import wait_and_validate_device_attribute_value
from tests.integration.conftest import ensure_checked_devices
from tests.settings import logger


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.test
def test_dln_kvalue_validation_result(change_event_callbacks):
    """Test Dish leaf node kvalue validation result"""
    dev_factory = DevFactory()
    central_node = DeviceProxy(CENTRALNODE_MID)
    ensure_checked_devices(central_node)
    dln_proxy = {
        "ska001": dev_factory.get_device(DISH_LEAF_NODE_1),
        "ska036": dev_factory.get_device(DISH_LEAF_NODE_36),
        "ska063": dev_factory.get_device(DISH_LEAF_NODE_63),
        "ska100": dev_factory.get_device(DISH_LEAF_NODE_100),
        "ska077": dev_factory.get_device(DISH_LEAF_NODE_77),
        "ska099": dev_factory.get_device(DISH_LEAF_NODE_099),
        "ska500": dev_factory.get_device(DISH_LEAF_NODE_500),
        "ska999": dev_factory.get_device(DISH_LEAF_NODE_999),
        "mkt001": dev_factory.get_device(DISH_LEAF_NODE_MKT),
    }

    # invoke the dish leaf node kValueValidationResult as FAILED
    for dl_node in dln_proxy.values():
        dl_node.SetDirectkValueValidationResult(str(int(ResultCode.FAILED)))

    assert wait_and_validate_device_attribute_value(
        central_node, "isdishvccconfigset", False
    ), "Timeout while waiting for validating attribute value"

    # Match the below values on dishVccValidationStatus
    dict_to_compare = {
        "mid-tmc/leaf-node-csp/0": "TMC and CSP Master Dish"
        + " Vcc Version is Same",
        "ska001": "k-value not identical",
        "ska036": "k-value not identical",
        "ska063": "k-value not identical",
        "ska100": "k-value not identical",
        "ska077": "k-value not identical",
        "ska099": "k-value not identical",
        "ska500": "k-value not identical",
        "ska999": "k-value not identical",
        "mkt001": "k-value not identical",
    }

    assert wait_and_validate_device_attribute_value(
        central_node,
        "DishVccValidationStatus",
        json.dumps(dict_to_compare),
        is_json=True,
    ), "Timeout while waiting for validating attribute value"

    # Verify if all dish leaf node gives k-value validation ResultCode.Ok

    for dl_node in dln_proxy.values():
        dl_node.SetDirectkValueValidationResult(str(int(ResultCode.OK)))

    assert wait_and_validate_device_attribute_value(
        central_node, "isdishvccconfigset", True
    ), "Timeout while waiting for validating attribute value"

    # Add validation for isdishvccconfigset

    logger.info("Subscribing isDishVccConfigSet")
    central_node.subscribe_event(
        "isDishVccConfigSet",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["isDishVccConfigSet"],
    )

    logger.info("Check if isDishVccConfigSet to True")
    change_event_callbacks["isDishVccConfigSet"].assert_change_event(
        True,
        lookahead=4,
    )

    result_string_to_match = {
        "dish": "ALL DISH OK",
        "mid-tmc/leaf-node-csp/0": "TMC and CSP Master Dish"
        + " Vcc Version is Same",
    }

    assert wait_and_validate_device_attribute_value(
        central_node,
        "DishVccValidationStatus",
        json.dumps(result_string_to_match),
        is_json=True,
    ), "Timeout while waiting for validating attribute value"

    logger.info("Check if DishVccValidationStatus to True")
    assert wait_and_validate_device_attribute_value(
        central_node,
        "DishVccValidationStatus",
        json.dumps(result_string_to_match),
    )

    # partial success
    dln_01 = dln_proxy["ska001"]
    dln_01.SetDirectkValueValidationResult(str("4"))
    assert wait_and_validate_device_attribute_value(
        central_node, "isdishvccconfigset", True
    ), "Timeout while waiting for validating attribute value"

    dict_to_compare = {
        "mid-tmc/leaf-node-csp/0": "TMC and CSP Master Dish"
        + " Vcc Version is Same",
        "ska001": "k-value not set",
    }
    assert wait_and_validate_device_attribute_value(
        central_node,
        "DishVccValidationStatus",
        json.dumps(dict_to_compare),
        is_json=True,
    ), "Timeout while waiting for validating attribute value"
    dln_01.SetDirectkValueValidationResult(str(int(ResultCode.OK)))

    result_string_to_match = {
        "dish": "ALL DISH OK",
        "mid-tmc/leaf-node-csp/0": "TMC and CSP Master Dish"
        + " Vcc Version is Same",
    }
    assert wait_and_validate_device_attribute_value(
        central_node,
        "DishVccValidationStatus",
        json.dumps(result_string_to_match),
        is_json=True,
    ), "Timeout while waiting for validating attribute value"
