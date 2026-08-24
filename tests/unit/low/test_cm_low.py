"""Module to test LOW component manager functionality."""

import json
from copy import deepcopy

import pytest

from ska_tmc_centralnode.model.input import InputParameterLow
from ska_tmc_centralnode.utils.constants import (
    LOW_ASSIGN_RESOURCES_SCHEMA_VERSION,
    LOW_RELEASE_RESOURCES_SCHEMA_VERSION,
)
from tests.settings import create_cm


def test_assign_release_version():
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))
    assert (
        cm.assign_resources_schema_version
        == LOW_ASSIGN_RESOURCES_SCHEMA_VERSION
    )
    cm.assign_resources_schema_version = "assign:1.2"
    assert cm.assign_resources_schema_version == "assign:1.2"
    assert (
        cm.release_resources_schema_version
        == LOW_RELEASE_RESOURCES_SCHEMA_VERSION
    )
    cm.release_resources_schema_version = "release:1.2"
    assert cm.release_resources_schema_version == "release:1.2"


def test_device_names():
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))
    assert (
        cm.get_mccs_master_leaf_node_dev_name() == "mid-tmc/leaf-node-mccs/0"
    )
    assert cm.get_mccs_master_dev_name() == "mid-mccs/control/0"


def test_stop_aggregation_process():
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))
    cm.stop_aggregation_process()
    assert not cm.aggregation_process.aggregation_process.is_alive()


def test_pss_mapping(json_factory, caplog):
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))
    assign_input_str = json_factory("assign_resource_low")
    valid_json = json.loads(assign_input_str)
    cm.update_subarray_pss_beams_mapping(valid_json)
    assert (
        cm.pss_beams_assigned_per_subarray[1]
        == valid_json["csp"]["pss"]["pss_beam_ids"]
    )
    cm.pss_beams_assigned_per_subarray.pop(1)
    json_copy = deepcopy(valid_json)
    json_copy.pop("csp")
    cm.update_subarray_pss_beams_mapping(json_copy)
    assert "csp key missing" in caplog.messages
    json_copy = deepcopy(valid_json)
    json_copy["csp"].pop("pss")
    cm.update_subarray_pss_beams_mapping(json_copy)
    assert not cm.pss_beams_assigned_per_subarray.get(json_copy["subarray_id"])
    json_copy = deepcopy(valid_json)
    conflicting_beams = json_copy["csp"]["pss"]["pss_beam_ids"]
    cm.pss_beams_assigned_per_subarray[2] = conflicting_beams
    error_msg = f"PSS beams: {conflicting_beams} already assigned"
    with pytest.raises(Exception) as exception:
        cm.update_subarray_pss_beams_mapping(json_copy)
    assert error_msg in str(exception.value)
    json_copy = deepcopy(valid_json)
    json_copy["csp"]["pss"].pop("pss_beam_ids")
    error_msg = "Exception occurred while updating subarray"
    with pytest.raises(Exception, match=error_msg):
        cm.update_subarray_pss_beams_mapping(json_copy)

    cm.set_pss_beams_assigned_per_subarray(3, conflicting_beams)
    assert cm.pss_beams_assigned_per_subarray[3] == conflicting_beams


def test_validate_assign_release_without_interface(json_factory):
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))
    release_input_str = json_factory("release_resource_low")
    release_json = json.loads(release_input_str)
    release_json.pop("interface")
    release_input = json.dumps(release_json)
    _, exception_msg = cm.validate_release_json(release_input)
    assert exception_msg == ""
    assign_input_str = json_factory("assign_resource_low")
    assign_json = json.loads(assign_input_str)
    assign_json.pop("interface")
    assign_input = json.dumps(assign_json)
    _, exception_msg = cm.validate_assign_json(assign_input)
    assert exception_msg == ""
