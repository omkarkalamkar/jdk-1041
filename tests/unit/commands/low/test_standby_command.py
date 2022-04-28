import time

import pytest
from ska_tango_base.commands import ResultCode
from ska_tmc_common.exceptions import CommandNotAllowed
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)
from ska_tmc_common.test_helpers.helper_state_mccsdevice import (
    HelperMCCSStateDevice,
)

from ska_tmc_centralnode.commands.telescope_standby_command import (
    TelescopeStandby,
)
from ska_tmc_centralnode.model.input import InputParameterLow

# from ska_tmc_common.test_helpers.helper_subarray_device import (
#     HelperSubArrayDevice,
# )
from tests.helpers.helper_subarray_device import HelperSubArrayDevice
from tests.settings import create_cm, logger


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": HelperSubArrayDevice,
            "devices": [{"name": "ska_low/tm_subarray_node/1"}],
        },
        {
            "class": HelperMCCSStateDevice,
            "devices": [
                {"name": "ska_low/tm_leaf_node/mccs_master"},
            ],
        },
    )


def test_low_telescope_standby_command(tango_context):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    cm, start_time = create_cm(input_parameter=InputParameterLow(None))
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )

    my_adapter_factory = HelperAdapterFactory()
    standby_command = TelescopeStandby(
        cm, cm.op_state_model, my_adapter_factory
    )
    assert standby_command.check_allowed()
    (result_code, _) = standby_command.do()
    assert result_code == ResultCode.OK
    for adapter in my_adapter_factory.adapters:
        adapter.proxy.Standby.assert_called()


def test_low_telescope_standby_command_fail_subarray(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm(input_parameter=InputParameterLow(None))
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    my_adapter_factory = HelperAdapterFactory()

    # include exception in TelescopeStandby command
    failing_dev = "ska_low/tm_subarray_node/1"

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


def test_low_telescope_standby_command_fail_mccs(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm(input_parameter=InputParameterLow(None))
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    my_adapter_factory = HelperAdapterFactory()

    # include exception in TelescopeStandby command
    failing_dev = "ska_low/tm_leaf_node/mccs_master"
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


def test_low_telescope_standby_fail_check_allowed(tango_context):

    logger.info("%s", tango_context)
    cm, start_time = create_cm(input_parameter=InputParameterLow(None))
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    my_adapter_factory = HelperAdapterFactory()
    cm.input_parameter.tm_subarray_dev_names = []
    standby_command = TelescopeStandby(
        cm, cm.op_state_model, my_adapter_factory
    )
    with pytest.raises(CommandNotAllowed):
        standby_command.check_allowed()
