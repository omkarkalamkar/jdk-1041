"""Test module for assign resources unavailability"""


import time

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from tango.db import Database

from ska_tmc_centralnode.utils.constants import (
    CENTRALNODE_LOW,
    CENTRALNODE_MID,
)
from tests.integration.conftest import get_cn_sn
from tests.settings import (
    LOW_SUBARRAY_DEVICE,
    LOW_SUBARRAY_NOT_AVAILABLE,
    MID_SUBARRAY_DEVICE,
    MID_SUBARRAY_NOT_AVAILABLE,
    assert_exception,
    check_subarray_availability,
    export_device,
    logger,
    telescope_off,
    telescope_on,
)


def assign_resources(
    central_node_fqdn,
    assign_input_str,
    change_event_callbacks,
    subarray_fqdn,
):
    """Assign Resources command method."""
    central_node_proxy, subarray_proxy, _ = get_cn_sn(central_node_fqdn)

    central_node_proxy.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    telescope_on(central_node_proxy, change_event_callbacks)

    subarray_proxy.SetisSubarrayAvailable(False)
    check_subarray_availability(central_node_proxy, subarray_fqdn, False)
    db = Database()
    db_device_info = db.get_device_info(subarray_fqdn)
    db.unexport_device(subarray_fqdn)

    # Waiting for event from central node
    time.sleep(3)
    msg = MID_SUBARRAY_NOT_AVAILABLE

    if "mid-tmc" in central_node_fqdn:
        result, unique_id = central_node_proxy.AssignResources(
            assign_input_str
        )
    else:
        result, unique_id = central_node_proxy.AssignResources(
            assign_input_str
        )
        msg = LOW_SUBARRAY_NOT_AVAILABLE
    logger.info(
        "AssignResources Command ID: %s Returned result: %s",
        unique_id,
        str(result),
    )

    # assert unique_id[0].endswith("AssignResources")
    assert result[0] == ResultCode.QUEUED
    assert_exception(
        unique_id,
        msg,
        change_event_callbacks,
        result_code=ResultCode.NOT_ALLOWED,
    )

    subarray_proxy.SetDirectObsState(ObsState.EMPTY)

    export_device(db, db_device_info)
    time.sleep(3)

    subarray_proxy.SetisSubarrayAvailable(True)
    check_subarray_availability(central_node_proxy, subarray_fqdn, True)

    # Teardown
    telescope_off(central_node_proxy, change_event_callbacks)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.parametrize(
    "central_node_name",
    [CENTRALNODE_MID],
)
@pytest.mark.usefixtures("set_mid_sdp_csp_admin_modes")
def test_assign_res_command_mid_unavailable_subarray(
    central_node_name,
    change_event_callbacks,
    json_factory,
):
    """Test Assign Resources command for low unavailable subarray for mid"""
    return assign_resources(
        central_node_name,
        json_factory("command_AssignResources"),
        change_event_callbacks,
        MID_SUBARRAY_DEVICE,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_low
@pytest.mark.parametrize(
    "central_node_name",
    [CENTRALNODE_LOW],
)
@pytest.mark.usefixtures("set_low_sdp_csp_mccs_admin_modes")
def test_assign_res_command_low_unavailable_subarray(
    central_node_name,
    change_event_callbacks,
    json_factory,
):
    """Test Assign Resources command for low unavailable subarray"""
    return assign_resources(
        central_node_name,
        json_factory("assign_resource_low"),
        change_event_callbacks,
        LOW_SUBARRAY_DEVICE,
    )
