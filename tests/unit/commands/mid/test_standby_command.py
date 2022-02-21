import time

import mock
import pytest
from ska_tango_base.base.base_device import SKABaseDevice
from ska_tango_base.commands import ResultCode

from ska_tmc_centralnode.commands.telescope_standby_command import (
    TelescopeStandby,
)
from ska_tmc_centralnode.exceptions import CommandNotAllowed
from ska_tmc_centralnode.manager.adapters import DishAdapter, SubArrayAdapter
from tests.helpers.helper_adapter_factory import HelperAdapterFactory
from tests.helpers.helper_subarray_device import HelperSubArrayDevice
from tests.settings import create_cm, logger


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": HelperSubArrayDevice,
            "devices": [{"name": "ska_mid/tm_subarray_node/1"}],
        },
        {
            "class": SKABaseDevice,
            "devices": [
                {"name": "ska_mid/tm_leaf_node/csp_master"},
                {"name": "ska_mid/tm_leaf_node/sdp_master"},
                {"name": "ska_mid/tm_leaf_node/d0001"},
            ],
        },
    )


def test_telescope_standby_command(tango_context):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    cm, start_time = create_cm()
    # num_faulty = count_faulty_devices(cm)
    # assert num_faulty == 0
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )

    my_adapter_factory = HelperAdapterFactory()
    standby_command = TelescopeStandby(
        cm, cm.op_state_model, my_adapter_factory
    )
    (result_code, _) = standby_command.do()
    assert result_code == ResultCode.OK
    for adapter in my_adapter_factory.adapters:
        if isinstance(adapter, DishAdapter):
            adapter.proxy.SetStandbyFPMode.assert_called()
            adapter.proxy.SetStandbyLPMode.assert_called()
            continue
        if isinstance(adapter, SubArrayAdapter):
            adapter.proxy.Standby.assert_called()
            continue

        adapter.proxy.Standby.assert_called()


def test_telescope_standby_command_fail_subarray(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    my_adapter_factory = HelperAdapterFactory()

    # include exception in TelescopeStandby command
    failing_dev = "ska_mid/tm_subarray_node/1"

    my_adapter_factory.get_or_create_adapter(
        failing_dev, attrs={"TelescopeStandBy.side_effect": Exception}
    )

    standby_command = TelescopeStandby(
        cm, cm.op_state_model, my_adapter_factory
    )
    assert standby_command.check_allowed()
    (result_code, message) = standby_command.do()
    assert result_code == ResultCode.FAILED
    assert failing_dev in message


def test_telescope_standby_command_fail_dish(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    my_adapter_factory = HelperAdapterFactory()

    # include exception in TelescopeStandby command
    failing_dev = "ska_mid/tm_leaf_node/d0001"

    attrs = {"SetStandbyFPMode.side_effect": Exception}
    dishMasterLeafMock = mock.Mock(**attrs)
    my_adapter_factory.get_or_create_adapter(
        failing_dev, proxy=dishMasterLeafMock
    )

    standby_command = TelescopeStandby(
        cm, cm.op_state_model, my_adapter_factory
    )
    assert standby_command.check_allowed()
    (result_code, message) = standby_command.do()
    assert result_code == ResultCode.FAILED
    assert failing_dev in message


def test_telescope_standby_fail_check_allowed(tango_context):

    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    my_adapter_factory = HelperAdapterFactory()
    cm.input_parameter.tm_dish_dev_names = []
    standby_command = TelescopeStandby(
        cm, cm.op_state_model, my_adapter_factory
    )
    with pytest.raises(CommandNotAllowed):
        standby_command.check_allowed()
