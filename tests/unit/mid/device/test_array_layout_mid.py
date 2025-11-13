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
from ska_tmc_centralnode.model.input import InputParameterMid
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
    assert cm.array_layout_url == mid_array_layout


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


def test_cm_default_array_layout_url_invalid_type_raises_value_error_mid():
    """Ensure CM command path raises ValueError for non-dict layout URL."""
    cm, _ = create_cm(_input_parameter=InputParameterMid(None))

    invalid_value = "this_is_not_a_dict"
    with pytest.raises(
        ValueError, match="default_array_layout_url must be a dictionary."
    ):
        cm.default_array_layout_url = invalid_value


def test_mid_assign_resources_fails_with_invalid_default_array_layout_json(
    tango_context,
    task_callback,
    set_mid_sdp_csp_admin_modes,
    monkeypatch,
):
    """
    If no telmodel is provided and the default array layout URL is not a dict,
    the AssignResources command should fail with the validation error.
    """
    cm, _ = create_cm(_input_parameter=InputParameterMid(None))

    # Ensure the command does NOT carry a 'telmodel' so the default is used
    assign_input_str = (
        get_assign_input_str()
    )  # reads command_AssignResources.json
    assign_input = json.loads(assign_input_str)
    assign_input.pop("telmodel", None)
    assign_input_str = json.dumps(assign_input)

    # Make subarray available (consistent with existing tests)
    dev_factory = DevFactory()
    subarray_device = dev_factory.get_device(MID_SUBARRAY_DEVICE)
    subarray_device.SetisSubarrayAvailable(True)
    check_if_subarray_is_available(cm)

    # Patch the CM's getter so default_array_layout_url returns a non-dict.
    # This avoids the setter ValueError test and directly exercises the command path.
    monkeypatch.setattr(
        cm.__class__,
        "default_array_layout_url",
        property(lambda self: "this_is_not_a_dict"),
    )

    # Invoke AssignResources via the CM path
    cm.assign_resources(assign_input_str, task_callback=task_callback)

    # Task lifecycle expectations with failure result
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (
                ResultCode.FAILED,
                "Invalid default 'telmodel': expected a dictionary.",
            ),
            "exception": "Invalid default 'telmodel': expected a dictionary.",
        }
    )

    # Sanity: the invalid value should not have been adopted
    assert cm.array_layout_url != "this_is_not_a_dict"
