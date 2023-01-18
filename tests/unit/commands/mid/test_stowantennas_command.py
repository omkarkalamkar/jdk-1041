import time

import mock
import pytest
from ska_tango_base.base.base_device import SKABaseDevice
from ska_tango_base.commands import ResultCode
from ska_tmc_common.adapters import DishAdapter
from ska_tmc_common.exceptions import CommandNotAllowed
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)
from ska_tmc_common.test_helpers.helper_subarray_device import (
    HelperSubArrayDevice,
)

from ska_tmc_centralnode.commands.stow_antennas_command import StowAntennas
from tests.settings import (
    DISH_LEAF_NODE_DEVICE,
    MID_CSP_MLN_DEVICE,
    MID_CSP_SLN_DEVICE,
    MID_SDP_MLN_DEVICE,
    MID_SDP_SLN_DEVICE,
    MID_SUBARRAY_DEVICE,
    create_cm,
    logger,
)


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": HelperSubArrayDevice,
            "devices": [
                {"name": MID_SUBARRAY_DEVICE},
                {"name": MID_CSP_SLN_DEVICE},
                {"name": MID_SDP_SLN_DEVICE},
            ],
        },
        {
            "class": SKABaseDevice,
            "devices": [
                {"name": MID_CSP_MLN_DEVICE},
                {"name": MID_SDP_MLN_DEVICE},
                {"name": DISH_LEAF_NODE_DEVICE},
            ],
        },
    )


@pytest.mark.skip(
    reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring."
)
def test_telescope_stow_antennas_command(tango_context):
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
    stow_command = StowAntennas(cm, cm.op_state_model, my_adapter_factory)
    (result_code, _) = stow_command.do(["1"])
    assert result_code == ResultCode.OK
    for adapter in my_adapter_factory.adapters:
        if isinstance(adapter, DishAdapter):
            adapter.proxy.SetStowMode.assert_called()


@pytest.mark.skip(
    reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring."
)
def test_telescope_stow_antennas_fail_dish(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    my_adapter_factory = HelperAdapterFactory()

    # include exception in SetStowMode command
    failing_dev = "ska_mid/tm_leaf_node/d0001"

    attrs = {"SetStowMode.side_effect": Exception}
    dishMasterLeafMock = mock.Mock(**attrs)
    my_adapter_factory.get_or_create_adapter(
        failing_dev, proxy=dishMasterLeafMock
    )

    stow_command = StowAntennas(cm, cm.op_state_model, my_adapter_factory)
    assert stow_command.check_allowed()
    (result_code, message) = stow_command.do(["1"])
    assert result_code == ResultCode.FAILED
    assert failing_dev in message


@pytest.mark.skip(
    reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring."
)
def test_telescope_stow_antennas_fail_check_allowed(tango_context):

    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    my_adapter_factory = HelperAdapterFactory()
    cm.input_parameter.tm_dish_dev_names = []
    stow_command = StowAntennas(cm, cm.op_state_model, my_adapter_factory)
    with pytest.raises(CommandNotAllowed):
        stow_command.check_allowed()
