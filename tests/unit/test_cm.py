"""Module to test common component manager functionality."""

import logging
import time
from unittest import mock

import pytest
from ska_control_model import TaskStatus

from tests.settings import create_cm


def test_array_layout_url(caplog):
    default_array_layout_url_mid = {
        "source_uris": [
            "gitlab://gitlab.com/ska-telescope/"
            "ska-telmodel-data?main#tmdata"
        ],
        "array_layout_path": ("instrument/ska1_low/layout/low-layout.json"),
    }
    cm, _ = create_cm()
    error_msg = "array_layout_url must be a dictionary."
    with pytest.raises(ValueError, match=error_msg):
        cm.array_layout_url = ""
    cm.array_layout_url = {}
    assert "Array layout URL set" not in caplog.records[0].message
    cm.default_array_layout_url = default_array_layout_url_mid
    assert "Default array layout URL set to" not in caplog.records[0].message
    cm.default_array_layout_url = {}
    assert cm.default_array_layout_url == {}


def test_stop_aggregation_process():
    cm, _ = create_cm()
    cm._stop_thread.set()
    time.sleep(0.3)  # max wait period
    assert not cm.aggregate_process_monitor_thread.is_alive()


def test_stop_all_process():
    cm, _ = create_cm()
    cm.stop_all_process()
    assert not cm.aggregation_process.aggregation_process.is_alive()
    assert not cm.aggregate_process_manager._process.is_alive()


def test_stop_event_manager(tango_context, caplog):
    caplog.set_level(logging.ERROR)
    cm, _ = create_cm()
    cm.stop_event_manager()
    for _, subs in cm.event_manager_object.device_subscriptions.items():
        assert not subs
    cm.setup_event_subscription()
    time.sleep(5)
    cm.event_manager_object.unsubscribe_event_async = mock.Mock(
        side_effect=Exception
    )
    error_msg = "Failed to unsubscribe event"
    cm.stop_event_manager()
    assert error_msg in caplog.records[-1].message


def test_stop():
    cm, _ = create_cm()
    cm.stop_liveliness_probe = mock.Mock()
    cm.stop_event_manager = mock.Mock()
    cm.stop()
    cm.stop_liveliness_probe.assert_called()
    cm.stop_event_manager.assert_called()
    assert cm._stop_thread.is_set()


def test_rejection():
    cm, _ = create_cm()
    command_not_implement = "Command is not Implemented"
    status, msg = cm.reset()
    assert status == TaskStatus.REJECTED
    assert msg == "Reset command is not implemented"
    status, msg = cm.off()
    assert status == TaskStatus.REJECTED
    assert command_not_implement in msg
    assert "Please use TelescopeOff command" in msg
    status, msg = cm.on()
    assert status == TaskStatus.REJECTED
    assert command_not_implement in msg
    assert "Please use TelescopeOn command" in msg
    status, msg = cm.standby()
    assert status == TaskStatus.REJECTED
    assert command_not_implement in msg
    assert "Please use TelescopeStandby command" in msg


def test_device_names():
    cm, _ = create_cm()
    assert cm.get_sdp_subarray_dev_names() == [
        "mid-tmc/subarray-leaf-node-sdp/01"
    ]
    assert cm.get_csp_subarray_dev_names() == [
        "mid-tmc/subarray-leaf-node-csp/01"
    ]
    assert cm.get_sdp_master_leaf_node_dev_name() == "mid-tmc/leaf-node-sdp/0"
    assert cm.get_csp_master_leaf_node_dev_name() == "mid-tmc/leaf-node-csp/0"
    assert cm.get_sdp_master_dev_name() == "mid-sdp/control/0"
    assert cm.get_csp_master_dev_name() == "mid-csp/control/0"


def test_update_unresponsiveness():
    cm, _ = create_cm()
    dev_info = mock.Mock()
    cm.get_device = mock.Mock(return_value=dev_info)
    cm._telescope_availability_aggregator.aggregate = mock.Mock()
    cm.update_responsiveness_info("abc")
    dev_info.update_unresponsive.assert_called_with(False, "")
    cm._telescope_availability_aggregator.aggregate.assert_called()
    cm.update_exception_for_unresponsiveness(dev_info, Exception("error"))
    dev_info.update_unresponsive.assert_called_with(True, "error")
    cm._telescope_availability_aggregator.aggregate.assert_called()


def test_input_valid():
    cm, _ = create_cm()
    valid, arg = cm.is_input_json_valid("{}")
    assert valid
    assert arg == {}
    valid, arg = cm.is_input_json_valid("{:}")
    assert not valid
    assert "Problem in loading the JSON string" in arg
    valid, sub_id = cm.check_subarray_id_in_json({"subarray_id": 1})
    assert valid and sub_id == 1
    valid, msg = cm.check_subarray_id_in_json({"": ""})
    assert not valid
    assert "subarray_id key is not present" in msg
