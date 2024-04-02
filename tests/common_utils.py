"""Utils folder for class test cases"""
import json
import logging
import time

from ska_tmc_common.dev_factory import DevFactory
from tango import DeviceProxy

from tests.settings import DISH_LEAF_NODE_DEVICE, MID_CSP_MLN_DEVICE


def tear_down(central_node_name, reset_sys_param=False):
    """Invoke command and set attributes required
    for tear down
    """
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_name)
    central_node.TelescopeOff()

    csp_master_ln_device = dev_factory.get_device(MID_CSP_MLN_DEVICE)
    dish_ln_device = dev_factory.get_device(DISH_LEAF_NODE_DEVICE)

    if reset_sys_param:
        csp_master_ln_device.ResetSysParams()
        dish_ln_device.SetKValue(0)


def is_device_ready(
    device_name: str, attribute_name: str, timeout: int = 20
) -> bool:
    """Wait for device to be ready
    Method read the atrribute value provided in argument and
    once device able to read attribute successfully then consider
    device is ready
    """
    dev_factory = DevFactory()
    count = 0
    # Wait for device to up within provided timeout
    while True:
        try:
            device_proxy = dev_factory.get_device(device_name)
            attr_value = device_proxy.read_attribute(attribute_name).value
            if attr_value == "":
                # if attribute is read successfully then
                # device is up and running
                return True
            logging.info(
                "Sleeping for 1 sec and cnt is %s and attribute value %s",
                count,
                attr_value,
            )
        except Exception as e:
            # if device is not started the exception is thrown
            logging.info(
                "Exception occurred while reading attribute %s and cnt is %s",
                e,
                count,
            )
        time.sleep(2)
        count += 1
        if count == timeout:
            return False


def wait_and_validate_device_attribute_value(
    device: DeviceProxy,
    attribute_name: str,
    expected_value: str,
    is_json: str = False,
    timeout: int = 20,
):
    """This method wait and validate if attribute value is equal to provided
    expected value
    """
    count = 0
    while count <= timeout:
        try:
            attribute_value = device.read_attribute(attribute_name).value
            if is_json and json.loads(attribute_value) == json.loads(
                expected_value
            ):
                return True
            if attribute_value == expected_value:
                return True
        except Exception as e:
            logging.info(
                "Exception occurred while reading attribute %s and cnt is %s",
                e,
                count,
            )
        count += 1
        time.sleep(1)
    return False
