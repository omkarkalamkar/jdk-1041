import logging
import time

from ska_tmc_common.dev_factory import DevFactory

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


def is_device_ready(device_name, attribute_name, timeout=20):
    """Wait for device to be ready
    Method read the atrribute value provided in argument and
    once device able to read attribute successfully then consider
    device is ready
    """
    dev_factory = DevFactory()
    cnt = 0
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
                cnt,
                attr_value,
            )
        except Exception as e:
            # if device is not started the exception is thrown
            logging.info(
                "Exception occurred while reading attribute %s and cnt is %s",
                e,
                cnt,
            )
        time.sleep(2)
        cnt += 1
        if cnt == timeout:
            return False
