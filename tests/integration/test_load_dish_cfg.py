import json

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory

from tests.integration.conftest import ensure_checked_devices
from tests.settings import MID_CSP_MLN_DEVICE, logger


def load_dish_cfg(
    tango_context,
    central_node_name,
    config_str,
    change_event_callbacks,
):
    logger.info("%s", config_str)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_name)

    ensure_checked_devices(central_node)

    result, unique_id = central_node.TelescopeOn()
    logger.info(
        f"TelescopeOn Command ID: {unique_id} Returned result: {result}"
    )

    assert unique_id[0].endswith("TelescopeOn")
    assert result[0] == ResultCode.QUEUED

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], str(int(ResultCode.OK))),
        lookahead=2,
    )

    result, unique_id = central_node.LoadDishCfg(config_str)
    logger.info(
        f"LoadDishCfg Command ID: {unique_id} Returned result: {result}"
    )

    assert unique_id[0].endswith("LoadDishCfg")
    assert result[0] == ResultCode.QUEUED

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], str(int(ResultCode.OK))),
        lookahead=4,
    )

    # Validate sysParams are set on Csp Master Device
    csp_master_ln_device = dev_factory.get_device(MID_CSP_MLN_DEVICE)
    assert json.dumps(csp_master_ln_device.sourceSysParam) == json.dumps(
        config_str
    )

    result, unique_id = central_node.TelescopeOff()


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.xfail(
    reason="Update in helper csp master leaf node required to pass"
)
@pytest.mark.parametrize(
    "central_node_name",
    [("ska_mid/tm_central/central_node")],
)
def test_load_dish_cfg(
    tango_context,
    central_node_name,
    change_event_callbacks,
    json_factory,
    set_mid_sdp_csp_mln_availability_for_aggregation,
):
    return load_dish_cfg(
        tango_context,
        central_node_name,
        json_factory("command_load_dish_cfg"),
        change_event_callbacks,
    )
