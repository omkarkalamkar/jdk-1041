import json
import time

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common import DevFactory
from tango.test_utils import DeviceTestContext

from ska_tmc_centralnode.central_node_low import LowTmcCentralNode
from ska_tmc_centralnode.model.input import InputParameterLow
from tests.settings import LOW_SUBARRAY_DEVICE, TIMEOUT, create_cm


@pytest.fixture
def central_node_device(request):
    """Create DeviceProxy for tests"""

    true_context = request.config.getoption("--true-context")
    if not true_context:
        with DeviceTestContext(LowTmcCentralNode, timeout=50) as proxy:
            yield proxy
    else:
        database = tango.Database()
        instance_list = database.get_device_exported_for_class(
            "LowTmcCentralNode"
        )
        for instance in instance_list.value_string:
            yield tango.DeviceProxy(instance)
            break


@pytest.fixture
def low_array_layout():
    """Common telmode dict for LOW array layout."""
    return {
        "source_uris": [
            "gitlab://gitlab.com/ska-telescope/ska-telmodel-data?main#tmdata"
        ],
        "array_layout_path": "instrument/ska1_low/layout/low-layout.json",
    }


@pytest.fixture
def low_array_layout_json(low_array_layout):
    """JSON form of the LOW array layout, for direct string comparisons."""
    return json.dumps(low_array_layout)


def test_array_layout_default_read_low(central_node_device):
    """Test to check DefaultarrayLayoutURL attribute value"""
    assert central_node_device.DefaultarrayLayoutURL == json.dumps(
        {
            "source_uris": [
                "gitlab://gitlab.com/ska-telescope/ska-telmodel-data?main#tmdata"
            ],
            "array_layout_path": "instrument/ska1_low/layout/low-layout.json",
        }
    )


def test_array_layout_default_write_low(central_node_device):
    """Test to check DefaultarrayLayoutURL attribute write"""
    new_default_array_layout = {
        "source_uris": [
            "gitlab://gitlab.com/ska-telescope/ska-telmodel-data?main#tmdata"
        ],
        "array_layout_path": "instrument/ska1_low/layout/modified-low-layout.json",
    }
    central_node_device.DefaultarrayLayoutURL = json.dumps(
        new_default_array_layout
    )
    assert (
        json.loads(central_node_device.DefaultarrayLayoutURL)
        == new_default_array_layout
    )


@pytest.mark.SKA_low
def test_low_assign_resources_command_without_array_layout(
    tango_context,
    task_callback,
    json_factory,
    low_array_layout,
    low_array_layout_json,
    set_low_sdp_csp_mccs_admin_modes,
):
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))

    dev_factory = DevFactory()
    subarray_device = dev_factory.get_device(LOW_SUBARRAY_DEVICE)
    subarray_device.SetisSubarrayAvailable(True)
    check_if_subarray_is_available(cm)
    assign_input = json_factory("assign_resource_low")

    assign_input = json.loads(assign_input)
    assign_input["telmodel"] = low_array_layout
    cm.assign_resources(json.dumps(assign_input), task_callback=task_callback)

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
        }
    )
    assert cm.array_layout_url == low_array_layout


# ---------- Helpers ----------


def check_if_subarray_is_available(cm):
    start_time = time.time()
    while (cm.component.telescope_availability)["tmc_subarrays"][
        LOW_SUBARRAY_DEVICE
    ] is not True:
        time.sleep(0.1)
        if time.time() - start_time > TIMEOUT:
            pytest.fail(
                "Timeout occurred while checking the SubarrayNode availability."
            )


def test_cm_default_array_layout_url_invalid_type_raises_value_error():
    """Ensure CM command path raises ValueError for non-dict layout URL."""
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))

    invalid_value = "this_is_not_a_dict"
    with pytest.raises(
        ValueError, match="default_array_layout_url must be a dictionary."
    ):
        cm.default_array_layout_url = invalid_value
