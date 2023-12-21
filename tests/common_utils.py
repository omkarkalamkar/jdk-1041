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


def wait_for_device_to_up(device_name, timeout=20):
    """Wait for device to up"""
    dev_factory = DevFactory()
    cnt = 0
    device_proxy = dev_factory.get_device(device_name)
    while device_proxy.ping() < 0:
        cnt += 1
        time.sleep(1)
        if cnt == timeout:
            break
