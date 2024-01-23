import json

import pytest
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from tango import DeviceProxy

from tests.common_utils import wait_and_validate_device_attribute_value
from tests.integration.conftest import ensure_checked_devices


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_dln_kvalue_validation_result(tango_context):
    dev_factory = DevFactory()
    central_node = DeviceProxy("ska_mid/tm_central/central_node")
    ensure_checked_devices(central_node)
    dish_leaf_node_01 = dev_factory.get_device("ska_mid/tm_leaf_node/d0001")

    dish_leaf_node_01.SetDirectkValueValidationResult(
        str(int(ResultCode.FAILED))
    )

    # invoke the dish leaf node kValueValidationResult as FAILED
    assert wait_and_validate_device_attribute_value(
        central_node, "isdishvccconfigset", False
    ), "Timeout while waiting for validating attribute value"

    # Match the below values on dishVccValidationStatus
    dict_to_compare = {
        "ska_mid/tm_leaf_node/csp_master": "TMC and CSP Master Dish Vcc Version is Same",
        "d0001": "k-value not identical",
    }
    assert wait_and_validate_device_attribute_value(
        central_node, "DishVccValidationStatus", json.dumps(dict_to_compare)
    ), "Timeout while waiting for validating attribute value"

    # Verify if all dish leaf node gives k-value validation result as ResultCode.Ok
    dish_leaf_node_01.SetDirectkValueValidationResult(str(int(ResultCode.OK)))

    assert wait_and_validate_device_attribute_value(
        central_node, "isdishvccconfigset", True
    ), "Timeout while waiting for validating attribute value"

    result_string_to_match = {
        "ska_mid/tm_leaf_node/csp_master": "TMC and CSP Master Dish Vcc Version is Same",
        "dish": "ALL DISH OK",
    }

    assert wait_and_validate_device_attribute_value(
        central_node,
        "DishVccValidationStatus",
        json.dumps(result_string_to_match),
    ), "Timeout while waiting for validating attribute value"
