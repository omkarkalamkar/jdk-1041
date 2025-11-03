"""Test case file"""

import json
import time
from os.path import dirname, join

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common import DevFactory
from tango.test_utils import DeviceTestContext

from ska_tmc_centralnode.central_node_mid import MidTmcCentralNode
from tests.settings import MID_SUBARRAY_DEVICE, TIMEOUT, create_cm, logger

# ---------- Fixtures ----------


@pytest.fixture
def central_node_device(request):
    """Create DeviceProxy for tests"""
    true_context = request.config.getoption("--true-context")
    if not true_context:
        with DeviceTestContext(MidTmcCentralNode, timeout=50) as proxy:
            yield proxy
    else:
        database = tango.Database()
        instance_list = database.get_device_exported_for_class(
            "MidTmcCentralNode"
        )
        for instance in instance_list.value_string:
            yield tango.DeviceProxy(instance)
            break


@pytest.fixture
def mid_array_layout():
    """Common telmode dict for MID array layout."""
    return {
        "source_uris": [
            "gitlab://gitlab.com/ska-telescope/ska-telmodel-data?main#tmdata"
        ],
        "array_layout_path": "instrument/ska1_mid/layout/mid-layout.json",
    }


@pytest.fixture
def mid_array_layout_json(mid_array_layout):
    """JSON form of the MID array layout, for direct string comparisons."""
    return json.dumps(mid_array_layout)


# ---------- Tests ----------


def test_array_layout_default_read_mid(central_node_device):
    """Test to check DefaultarrayLayoutURL attribute value"""
    assert central_node_device.DefaultarrayLayoutURL == json.dumps(
        {
            "source_uris": [
                "gitlab://gitlab.com/ska-telescope/ska-telmodel-data?main#tmdata"
            ],
            "array_layout_path": "instrument/ska1_mid/layout/mid-layout.json",
        }
    )


def test_array_layout_default_write_mid(central_node_device):
    """Test to check DefaultarrayLayoutURL attribute write"""
    new_default_array_layout = {
        "source_uris": [
            "gitlab://gitlab.com/ska-telescope/ska-telmodel-data?main#tmdata"
        ],
        "array_layout_path": "instrument/ska1_mid/layout/modified-mid-layout.json",
    }
    central_node_device.DefaultarrayLayoutURL = json.dumps(
        new_default_array_layout
    )
    assert (
        json.loads(central_node_device.DefaultarrayLayoutURL)
        == new_default_array_layout
    )


"""Test case file"""


def get_assign_input_str(assign_input_file="command_AssignResources.json"):
    """Assign Input String"""
    path = join(dirname(__file__), "..", "..", "..", "data", assign_input_file)
    with open(path, "r") as f:
        assign_input_str = f.read()
    return assign_input_str


def test_array_layout_assign_resources(
    tango_context, task_callback, set_mid_sdp_csp_admin_modes, mid_array_layout
):
    """Tests assign Resources completed"""
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.is_dish_vcc_config_set = True
    result = cm.is_command_allowed("AssignResources")
    logger.info(f"Command allowed result is: {result}")

    assign_input_str = get_assign_input_str()
    assign_input_str = json.loads(assign_input_str)
    assign_input_str["telmodel"] = mid_array_layout
    assign_input_str = json.dumps(assign_input_str)
    dev_factory = DevFactory()
    subarray_device = dev_factory.get_device(MID_SUBARRAY_DEVICE)

    subarray_device.SetisSubarrayAvailable(True)
    check_if_subarray_is_available(cm)

    cm.assign_resources(assign_input_str, task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )

    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.OK, "Command Completed"),
        },
        lookahead=5,
    )


def check_if_subarray_is_available(cm):
    start_time = time.time()
    elapsed_time = 0
    while (cm.component.telescope_availability)["tmc_subarrays"][
        MID_SUBARRAY_DEVICE
    ] is not True:
        elapsed_time = time.time() - start_time
        time.sleep(0.1)
        if elapsed_time > TIMEOUT:
            pytest.fail(
                "Timeout occurred while checking the SubarrayNode availability."
            )
