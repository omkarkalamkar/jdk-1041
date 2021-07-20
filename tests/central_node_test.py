# Standard Python imports
import contextlib
import importlib
import sys
import types
import json
import pytest
import mock
import logging
from mock import MagicMock
from mock import Mock
from os.path import dirname, join
import threading

# Tango imports
import tango
from tango import DevState
from tango.test_context import DeviceTestContext
from tmc.centralnode.standby_command import Standby
from tmc.centralnode.telescope_standby_command import TelescopeStandby
from tmc.centralnode.on_command import On
from tmc.centralnode.telescope_on_command import TelescopeOn
from ska.base.control_model import ObsState
from ska.base import SKASubarrayStateModel

from tmc.common.tango_client import TangoClient
from tmc.common.tango_server_helper import TangoServerHelper
from tmc.centralnode.device_data import DeviceData
from tmc.centralnode.off_command import Off
from tmc.centralnode.input_validator import AssignResourceValidator
from tmc.centralnode.op_state_aggregator import OpStateAggregator
from tmc.centralnode.telescope_state_aggregator import TelescopeStateAggregator
from tmc.centralnode import CentralNode, const, release
from tmc.centralnode.const import (
    CMD_SET_STOW_MODE,
    STR_ON_CMD_ISSUED,
    STR_STOW_CMD_ISSUED_CN,
    STR_TELESCOPE_OFF_CMD_ISSUED,
    ModesAvailability,
)
from ska.base.control_model import (
    HealthState,
    AdminMode,
    SimulationMode,
    ControlMode,
    TestMode,
)
from ska.base.control_model import LoggingLevel
from ska.base.commands import ResultCode
from ska.base import SKASubarrayStateModel

assign_input_file = "command_AssignResources.json"
path = join(dirname(__file__), "data", assign_input_file)
with open(path, "r") as f:
    assign_input_str = f.read()

release_input_file = "command_ReleaseResources.json"
path = join(dirname(__file__), "data", release_input_file)
with open(path, "r") as f:
    release_input_str = f.read()

invalid_json_Assign_Release_file = "invalid_json_Assign_Release_Resources.json"
path = join(dirname(__file__), "data", invalid_json_Assign_Release_file)
with open(path, "r") as f:
    assign_release_invalid_str = f.read()

assign_invalid_key_file = "invalid_key_AssignResources.json"
path = join(dirname(__file__), "data", assign_invalid_key_file)
with open(path, "r") as f:
    assign_invalid_key = f.read()

release_invalid_key_file = "invalid_key_ReleaseResources.json"
path = join(dirname(__file__), "data", release_invalid_key_file)
with open(path, "r") as f:
    release_invalid_key = f.read()

device_data = DeviceData.get_instance()


@pytest.fixture
def subarray_state_model():
    """
    Yields a new SKASubarrayStateModel for testing
    """
    yield SKASubarrayStateModel(logging.getLogger())


@pytest.fixture(scope="function")
def mock_subarraynode_device(mock_tango_server_helper, mock_tango_client):
    subarray1_fqdn = "ska_mid/tm_subarray_node/1"
    dut_properties = {"TMMidSubarrayNodes": "ska_mid/tm_subarray_node/1"}
    tango_server_obj = mock_tango_server_helper
    tango_client_obj = mock_tango_client
    event_subscription_map = {}
    subarray1_device_proxy_mock = Mock()
    Mock().subscribe_event.side_effect = lambda attr_name, event_type, callback, *args, **kwargs: event_subscription_map.update(
        {attr_name: callback}
    )
    with fake_tango_system(
        CentralNode, initial_dut_properties=dut_properties
    ) as tango_context:
        yield tango_context.device, tango_client_obj, dut_properties[
            "TMMidSubarrayNodes"
        ], event_subscription_map, tango_server_obj


@pytest.fixture(scope="function", params=[HealthState.UNKNOWN])
def health_state(request):
    return request.param


@pytest.fixture(scope="function")
def mock_obstate_check():
    dut_properties = {"TMMidSubarrayNodes": "ska_mid/tm_subarray_node/1"}
    with mock.patch.object(
        TangoClient, "_get_deviceproxy", return_value=Mock()
    ) as mock_obj:
        tango_client_obj = TangoClient(dut_properties["TMMidSubarrayNodes"])
        with mock.patch.object(
            TangoClient, "get_attribute", Mock(return_value=ObsState.EMPTY)
        ) as mock_obj_obstate:
            yield tango_client_obj


def dummy_subscriber(attribute, callback_method):
    fake_event = Mock()
    fake_event.err = False
    fake_event.attr_name = f"ska_mid/tm_leaf_node/csp_master/{attribute}"
    fake_event.attr_value.value = HealthState.UNKNOWN
    callback_method(fake_event)
    return 10


@pytest.fixture(scope="function")
def mock_tango_server_helper():
    with mock.patch.object(
        TangoServerHelper,
        "read_property",
        return_value=(
            "ska_mid/tm_subarray_node/1",
            "ska_mid/tm_leaf_node/csp_subarray01",
            "ska_mid/tm_leaf_node/sdp_subarray01",
            "ska_mid/tm_leaf_node/d0001",
            "ska_mid/tm_leaf_node/sdp_master",
            "ska_mid/tm_leaf_node/csp_master",
            "mid_csp/elt/master",
            "mid_sdp/elt/master",
            "mid_d0001/elt/master",
        ),
    ) as mock_obj:
        tango_server_obj = TangoServerHelper.get_instance()
        yield tango_server_obj


def dummy_subscriber_State(attribute, fqdn, state):
    fake_event = Mock()
    fake_event.err = False
    fake_event.attr_name = f"{fqdn}/{attribute}"
    fake_event.attr_value.value = state
    return fake_event


@pytest.mark.skip(reason="Test case is failing radmonly")
def test_state_aggregator_callback(mock_subarray):
    device_proxy, tango_client_obj, _ = mock_subarray
    device_proxy.On()
    state_aggr = OpStateAggregator()
    state_aggr.state_callback(
        dummy_subscriber_State("State", "ska_mid/tm_subarray_node/1", DevState.ON)
    )
    state_aggr.state_callback(
        dummy_subscriber_State(
            "State", "ska_mid/tm_leaf_node/csp_subarray01", DevState.ON
        )
    )
    state_aggr.state_callback(
        dummy_subscriber_State(
            "State", "ska_mid/tm_leaf_node/sdp_subarray01", DevState.ON
        )
    )
    state_aggr.state_callback(
        dummy_subscriber_State("State", "ska_mid/tm_leaf_node/d0001", DevState.ON)
    )
    state_aggr.state_callback(
        dummy_subscriber_State("State", "ska_mid/tm_leaf_node/sdp_master", DevState.ON)
    )
    state_aggr.state_callback(
        dummy_subscriber_State("State", "ska_mid/tm_leaf_node/csp_master", DevState.ON)
    )
    assert device_proxy.state() == DevState.ON


def dummy_subscriber_telescopeState(attribute, fqdn, telescope_state):
    fake_event = Mock()
    fake_event.err = False
    fake_event.attr_name = f"{fqdn}/{attribute}"
    fake_event.attr_value.value = telescope_state
    return fake_event


@pytest.mark.skip(reason="Behaviour of the test case is random")
def test_telescopeState_aggregator_callback(mock_subarray):
    device_proxy, tango_client_obj, _ = mock_subarray
    device_proxy.On()
    telescope_state_aggr = TelescopeStateAggregator()
    telescope_state_aggr.telescope_state_callback(
        dummy_subscriber_telescopeState("State", "mid_csp/elt/master", DevState.ON)
    )
    telescope_state_aggr.telescope_state_callback(
        dummy_subscriber_telescopeState("State", "mid_sdp/elt/master", DevState.ON)
    )
    telescope_state_aggr.telescope_state_callback(
        dummy_subscriber_telescopeState("State", "mid_d0001/elt/master", DevState.ON)
    )
    assert device_proxy.telescopeState == DevState.ON


@pytest.fixture(
    scope="function",
    params=[
        HealthState.DEGRADED,
        HealthState.OK,
        HealthState.UNKNOWN,
        HealthState.FAILED,
    ],
)
def central_node_test_info(request):
    device_under_test = CentralNode
    csp_master_fqdn = "mid_csp/elt/master"
    csp_master_health_attribute = "healthState"

    initial_dut_properties = {"CspMasterLeafNodeFQDN": csp_master_fqdn}

    event_subscription_map = {}
    csp_master_proxy_mock = Mock()
    csp_master_proxy_mock.subscribe_event.side_effect = lambda attr_name, event_type, callback, *args, **kwargs: event_subscription_map.update(
        {attr_name: callback}
    )

    proxies_to_mock = {csp_master_fqdn: csp_master_proxy_mock}

    test_info = {
        "csp_master_health_attribute": csp_master_health_attribute,
        "initial_dut_properties": initial_dut_properties,
        "proxies_to_mock": proxies_to_mock,
        "csp_master_health_state": request.param,
        "event_subscription_map": event_subscription_map,
        "csp_master_fqdn": csp_master_fqdn,
    }
    return test_info


def test_standby_class_command_method(subarray_state_model, mock_subarray):
    _, tango_client_obj, _ = mock_subarray
    standby_cmd = Standby(device_data, subarray_state_model)
    subarray_state_model._straight_to_state(DevState.ON, None)
    standby_cmd.do()
    tango_client_obj.deviceproxy.command_inout.assert_called_with(
        const.CMD_STANDBY, None
    )


def test_on_class_command_method(subarray_state_model, mock_subarray):
    _, tango_client_obj, _ = mock_subarray
    on_cmd = On(device_data, subarray_state_model)
    subarray_state_model._straight_to_state(DevState.ON, None)
    on_cmd.do()
    tango_client_obj.deviceproxy.command_inout.assert_called_with(const.CMD_ON, None)


def test_telescope_on_class_command_method(subarray_state_model, mock_subarray):
    device_proxy, tango_client_obj, _ = mock_subarray
    telescope_on_cmd = TelescopeOn(device_data, subarray_state_model)
    subarray_state_model._straight_to_state(DevState.ON, None)
    telescope_on_cmd.do()
    tango_client_obj.deviceproxy.command_inout.assert_called_with(
        const.CMD_TELESCOPE_ON, None
    )
    assert device_proxy.desiredTelescopeState == DevState.ON


def test_telescope_standby_class_command_method(subarray_state_model, mock_subarray):
    device_proxy, tango_client_obj, _ = mock_subarray
    telescope_standby_cmd = TelescopeStandby(device_data, subarray_state_model)
    subarray_state_model._straight_to_state(DevState.ON, None, ObsState.EMPTY)
    telescope_standby_cmd.do()
    tango_client_obj.deviceproxy.command_inout_asynch.assert_called_with(
        const.CMD_TELESCOPE_STANDBY,
        None,
        any_method(with_name="telescopestandby_cmd_ended_cb"),
    )
    assert device_proxy.desiredTelescopeState == DevState.STANDBY


def test_telescope_off(mock_obstate_check, mock_subarray):
    device_proxy, tango_client_obj, _ = mock_subarray
    tango_client_obj.get_attribute.side_effect = Mock(return_value=ObsState.EMPTY)
    device_proxy.TelescopeOn()
    device_proxy.TelescopeOff()
    assert device_proxy.activityMessage == const.STR_TELESCOPE_OFF_CMD_ISSUED
    assert device_proxy.desiredTelescopeState == DevState.OFF


# Mocking AssignResources command success response from SubarrayNode
def mock_subarray_call_assign_resources_success(arg1, arg2):
    arg = json.loads(assign_input_str)
    argout = [str(arg["dish"]["receptor_ids"])]
    return [ResultCode.STARTED, argout]


# Mocking ReleaseResources command success response from SubarrayNode
def mock_subarray_call_release_resources_success(arg1, arg2):
    argout = ["[]"]
    return [ResultCode.STARTED, argout]


@pytest.fixture(scope="function")
def mock_tango_client():
    with mock.patch.object(
        TangoClient, "_get_deviceproxy", return_value=MagicMock()
    ) as mock_obj:
        tango_client_obj = TangoClient("ska_mid/tm_subarray_node/1")
        yield tango_client_obj


@pytest.fixture(scope="function")
def mock_subarray(mock_tango_server_helper, mock_tango_client):
    tango_client_obj = mock_tango_client
    tango_server_obj = mock_tango_server_helper
    subarray1_fqdn = "ska_mid/tm_subarray_node/1"
    tm_subarrays = []
    tm_subarrays.append(subarray1_fqdn)
    dut_properties = {"TMMidSubarrayNodes": tm_subarrays, "NumDishes": 4}
    with fake_tango_system(
        CentralNode, initial_dut_properties=dut_properties
    ) as tango_context:
        yield tango_context.device, tango_client_obj, tango_server_obj


def test_off_class_command_method(subarray_state_model, mock_subarray):
    _, tango_client_obj, _ = mock_subarray
    device_data = DeviceData.get_instance()
    off_cmd = Off(device_data, subarray_state_model)
    subarray_state_model._straight_to_state(DevState.ON, None)
    off_cmd.do()
    tango_client_obj.deviceproxy.command_inout.assert_called_with(const.CMD_OFF, None)


def test_assign_resources(mock_subarray):
    device_proxy, tango_client_obj, tango_server_obj = mock_subarray
    tango_server_obj.read_property.side_effect = Mock(
        return_value=[
            "ska_mid/tm_subarray_node/1",
            "ska_mid/tm_subarray_node/2",
            "ska_mid/tm_subarray_node/3",
        ]
    )
    # mocking subarray device state as ON as per new state model
    tango_client_obj.DevState = DevState.ON
    receptor_ids_success = []
    receptor_ids_success.append("0001")
    dish = {}
    dish["receptor_ids_success"] = receptor_ids_success
    success_response = {}
    success_response["dish"] = dish
    tango_client_obj.deviceproxy.command_inout.side_effect = (
        mock_subarray_call_assign_resources_success
    )
    message = device_proxy.AssignResources(assign_input_str)
    assert json.loads(message) == success_response


def test_assign_resources_should_raise_devfailed_exception_when_subarray_node_throws_devfailed_exception(
    mock_subarray,
):
    device_proxy, tango_client_obj, tango_server_obj = mock_subarray
    tango_server_obj.read_property.side_effect = Mock(
        return_value=[
            "ska_mid/tm_subarray_node/1",
            "ska_mid/tm_subarray_node/2",
            "ska_mid/tm_subarray_node/3",
        ]
    )
    tango_client_obj.DevState = DevState.OFF
    tango_client_obj.deviceproxy.command_inout.side_effect = raise_devfailed_exception
    with pytest.raises(tango.DevFailed) as df:
        device_proxy.AssignResources(assign_input_str)
    assert "Error occurred while assigning resources to the Subarray" in str(df)


def test_assign_resources_invalid_json_value(
    mock_tango_server_helper, mock_tango_client
):
    tango_server_obj = mock_tango_server_helper
    tango_server_obj.read_property.side_effect = Mock(
        return_value=[
            "ska_mid/tm_subarray_node/1",
            "ska_mid/tm_subarray_node/2",
            "ska_mid/tm_subarray_node/3",
        ]
    )
    with fake_tango_system(CentralNode) as tango_context:
        with pytest.raises(tango.DevFailed) as df:
            tango_context.device.AssignResources(assign_release_invalid_str)
        assert const.STR_RESOURCE_ALLOCATION_FAILED in str(df.value)


def test_assign_resources_invalid_key(mock_tango_server_helper, mock_tango_client):
    tango_server_obj = mock_tango_server_helper
    tango_server_obj.read_property.side_effect = Mock(
        return_value=[
            "ska_mid/tm_subarray_node/1",
            "ska_mid/tm_subarray_node/2",
            "ska_mid/tm_subarray_node/3",
        ]
    )
    with fake_tango_system(CentralNode) as tango_context:
        result = "test"
        with pytest.raises(tango.DevFailed):
            result = tango_context.device.AssignResources(assign_invalid_key)
        assert "test" in result


def test_assign_resources_raise_devfailed_when_reseource_reallocation(
    mock_tango_server_helper, mock_tango_client
):
    tango_server_obj = mock_tango_server_helper
    tango_server_obj.read_property.side_effect = Mock(
        return_value=[
            "ska_mid/tm_subarray_node/1",
            "ska_mid/tm_subarray_node/2",
            "ska_mid/tm_subarray_node/3",
        ]
    )
    subarray1_fqdn = "ska_mid/tm_subarray_node/1"
    subarray2_fqdn = "ska_mid/tm_subarray_node/2"
    tm_subarrays = []
    tm_subarrays.append(subarray1_fqdn)
    tm_subarrays.append(subarray2_fqdn)
    dut_properties = {"TMMidSubarrayNodes": tm_subarrays, "NumDishes": 4}

    with fake_tango_system(
        CentralNode, initial_dut_properties=dut_properties
    ) as tango_context:
        device_proxy = tango_context.device
        receptor_ids_success = []
        receptor_ids_success.append("0001")
        dish = {}
        dish["receptor_ids_success"] = receptor_ids_success
        success_response = {}
        success_response["dish"] = dish
        with mock.patch.object(
            TangoClient, "_get_deviceproxy", return_value=MagicMock()
        ) as mock_obj:
            tango_client_obj = TangoClient(subarray1_fqdn)
            tango_client_obj.deviceproxy.command_inout.side_effect = (
                mock_subarray_call_assign_resources_success
            )
            message = device_proxy.AssignResources(assign_input_str)
            assert json.loads(message) == success_response
            reallocation_request = json.loads(assign_input_str)
            reallocation_request["subarray_id"] = 2
            with pytest.raises(tango.DevFailed) as df:
                device_proxy.AssignResources(json.dumps(reallocation_request))
            assert const.ERR_RECEPTOR_ID_REALLOCATION in str(df.value)


# Test cases for Attributes
def test_telescope_health_state():
    with fake_tango_system(CentralNode) as tango_context:
        assert tango_context.device.telescopeHealthState == HealthState.UNKNOWN


def test_telescope_state():
    with fake_tango_system(CentralNode) as tango_context:
        assert tango_context.device.telescopeState == DevState.STANDBY


def test_imaging():
    with fake_tango_system(CentralNode) as tango_context:
        assert tango_context.device.imaging == ModesAvailability.not_available


def test_pss():
    with fake_tango_system(CentralNode) as tango_context:
        assert tango_context.device.pss == ModesAvailability.not_available


def test_pst():
    with fake_tango_system(CentralNode) as tango_context:
        assert tango_context.device.pst == ModesAvailability.not_available


def test_vlbi():
    with fake_tango_system(CentralNode) as tango_context:
        assert tango_context.device.vlbi == ModesAvailability.not_available


def test_activity_message():
    with fake_tango_system(CentralNode) as tango_context:
        tango_context.device.activityMessage = ""
        assert tango_context.device.activityMessage == ""


def test_logging_level():
    with fake_tango_system(CentralNode) as tango_context:
        tango_context.device.loggingLevel = LoggingLevel.INFO
        assert tango_context.device.loggingLevel == LoggingLevel.INFO


def test_logging_targets():
    with fake_tango_system(CentralNode) as tango_context:
        tango_context.device.loggingTargets = ["console::cout"]
        assert "console::cout" in tango_context.device.loggingTargets


def test_test_mode():
    with fake_tango_system(CentralNode) as tango_context:
        test_mode = TestMode.NONE
        tango_context.device.testMode = test_mode
        assert tango_context.device.testMode == test_mode


def test_simulation_mode():
    with fake_tango_system(CentralNode) as tango_context:
        simulation_mode = SimulationMode.FALSE
        tango_context.device.simulationMode = simulation_mode
        assert tango_context.device.simulationMode == simulation_mode


def test_control_mode():
    with fake_tango_system(CentralNode) as tango_context:
        control_mode = ControlMode.REMOTE
        tango_context.device.controlMode = control_mode
        assert tango_context.device.controlMode == control_mode


def test_health_state():
    with fake_tango_system(CentralNode) as tango_context:
        assert tango_context.device.healthState == HealthState.OK


# # Test cases for commands
def test_stow_antennas_should_set_stow_mode_on_leaf_nodes(
    mock_tango_server_helper, mock_tango_client
):
    tango_server_obj = mock_tango_server_helper
    tango_server_obj.read_property.side_effect = Mock(return_value=["fqdn"])
    dish_device_ids = [str(i).zfill(4) for i in range(1, 4)]
    fqdn_prefix = "ska_mid/tm_leaf_node/d"
    initial_dut_properties = {
        "DishLeafNodePrefix": fqdn_prefix,
        "NumDishes": len(dish_device_ids),
    }
    with fake_tango_system(CentralNode, initial_dut_properties) as tango_context:
        with mock.patch.object(
            TangoClient, "_get_deviceproxy", return_value=Mock()
        ) as mock_obj:
            tango_client_obj = TangoClient(
                initial_dut_properties["DishLeafNodePrefix"] + dish_device_ids[0]
            )
            tango_context.device.StowAntennas(dish_device_ids)
            # for proxy_mock in proxies_to_mock.values():
            tango_client_obj.deviceproxy.command_inout.assert_called_with(
                CMD_SET_STOW_MODE, None
            )


def test_stow_antennas_should_raise_devfailed_exception(
    mock_tango_server_helper, mock_tango_client
):
    tango_server_obj = mock_tango_server_helper
    tango_server_obj.read_property.side_effect = Mock(return_value=["fqdn"])
    dish_device_ids = [str(i).zfill(4) for i in range(1, 4)]
    fqdn_prefix = "ska_mid/tm_leaf_node/d"
    initial_dut_properties = {
        "DishLeafNodePrefix": fqdn_prefix,
        "NumDishes": len(dish_device_ids),
    }

    with fake_tango_system(CentralNode, initial_dut_properties) as tango_context:
        with mock.patch.object(
            TangoClient, "_get_deviceproxy", return_value=Mock()
        ) as mock_obj:
            tango_client_obj = TangoClient(
                initial_dut_properties["DishLeafNodePrefix"] + dish_device_ids[0]
            )
            tango_client_obj.deviceproxy.command_inout.side_effect = (
                raise_devfailed_exception
            )
            with pytest.raises(tango.DevFailed) as df:
                tango_context.device.StowAntennas(dish_device_ids)
            assert const.ERR_EXE_STOW_CMD in str(df.value)


#     """Negative Test for StowAntennas"""
def test_stow_antennas_invalid_value(mock_tango_server_helper, mock_tango_client):
    tango_server_obj = mock_tango_server_helper
    tango_server_obj.read_property.side_effect = Mock(return_value=["fqdn"])
    with fake_tango_system(CentralNode) as tango_context:
        argin = [
            "invalid_antenna",
        ]
        with pytest.raises(tango.DevFailed) as df:
            tango_context.device.StowAntennas(argin)

        assert const.ERR_STOW_ARGIN in str(df.value)


def test_release_resources(mock_subarray):
    device_proxy, tango_client_obj, _ = mock_subarray
    release_all_success = {"release_all": True, "receptor_ids": []}
    tango_client_obj.deviceproxy.command_inout.side_effect = (
        mock_subarray_call_release_resources_success
    )
    message = device_proxy.ReleaseResources(release_input_str)
    assert json.dumps(release_all_success) in message


def test_release_resources_should_raise_devfailed_exception(
    mock_tango_server_helper, mock_tango_client
):
    tango_server_obj = mock_tango_server_helper
    tango_server_obj.read_property.side_effect = Mock(return_value=["fqdn"])
    subarray1_fqdn = "ska_mid/tm_subarray_node/1"
    dut_properties = {"TMMidSubarrayNodes": subarray1_fqdn}
    with fake_tango_system(
        CentralNode, initial_dut_properties=dut_properties
    ) as tango_context:
        with mock.patch.object(
            TangoClient, "_get_deviceproxy", return_value=Mock()
        ) as mock_obj:
            tango_client_obj = TangoClient(dut_properties["TMMidSubarrayNodes"])
            tango_client_obj.deviceproxy.command_inout.side_effect = (
                raise_devfailed_exception
            )
            with pytest.raises(tango.DevFailed) as df:
                tango_context.device.ReleaseResources(release_input_str)
            assert const.ERR_DEVFAILED_MSG in str(df.value)


def test_release_resources_invalid_json_value(
    mock_tango_server_helper, mock_tango_client
):
    tango_server_obj = mock_tango_server_helper
    tango_server_obj.read_property.side_effect = Mock(return_value=["fqdn"])
    with fake_tango_system(CentralNode) as tango_context:
        with pytest.raises(tango.DevFailed) as df:
            tango_context.device.ReleaseResources(assign_release_invalid_str)
        assert const.ERR_INVALID_JSON in str(df.value)


def test_release_resources_invalid_key(mock_tango_server_helper, mock_tango_client):
    tango_server_obj = mock_tango_server_helper
    tango_server_obj.read_property.side_effect = Mock(return_value=["fqdn"])
    with fake_tango_system(CentralNode) as tango_context:
        with pytest.raises(tango.DevFailed) as df:
            tango_context.device.ReleaseResources(release_invalid_key)
        assert const.ERR_JSON_KEY_NOT_FOUND in str(df.value)


@pytest.fixture(scope="function", params=[("TelescopeOn")])
def command_without_arg_devfailed(request):
    cmd_name = request.param
    return cmd_name


def test_command_without_arg_should_raise_devfailed_exception(
    mock_subarray, command_without_arg_devfailed, mock_tango_server_helper
):
    device_proxy, tango_client, _ = mock_subarray
    cmd_name = command_without_arg_devfailed
    tango_client.deviceproxy.command_inout.side_effect = raise_devfailed_exception
    with pytest.raises(tango.DevFailed):
        device_proxy.command_inout(cmd_name)
    assert device_proxy.state() == DevState.FAULT


def test_telescopeoff_should_raise_devfailed_exception(
    mock_subarray, mock_tango_server_helper
):
    device_proxy, tango_client, _ = mock_subarray
    tango_client.deviceproxy.command_inout.side_effect = raise_devfailed_exception
    with pytest.raises(tango.DevFailed):
        device_proxy.TelescopeOn()
        device_proxy.TelescopeOff()
    assert device_proxy.state() == DevState.FAULT


# Test cases for Telescope Health State
@pytest.fixture(scope="function")
def mock_csp_master_proxy(mock_tango_server_helper, mock_tango_client):
    dut_properties = {"CspMasterFQDN": "mid_csp/elt/master"}
    event_subscription_map = {}
    Mock().subscribe_event.side_effect = lambda attr_name, event_type, callback, *args, **kwargs: event_subscription_map.update(
        {attr_name: callback}
    )
    with fake_tango_system(
        CentralNode, initial_dut_properties=dut_properties
    ) as tango_context:
        with mock.patch.object(
            TangoClient, "_get_deviceproxy", return_value=Mock()
        ) as mock_obj:
            tango_client_obj = TangoClient(dut_properties["CspMasterFQDN"])
            yield tango_context.device, tango_client_obj, dut_properties[
                "CspMasterFQDN"
            ], event_subscription_map


def test_telescope_health_state_matches_csp_master_leaf_node_health_state_after_start(
    mock_csp_master_proxy, health_state, mock_tango_server_helper
):
    (
        device_proxy,
        tango_client_obj,
        csp_master_fqdn,
        event_subscription_map,
    ) = mock_csp_master_proxy
    tango_server_obj = mock_tango_server_helper
    tango_server_obj.read_property.side_effect = Mock(return_value=["fqdn"])
    with mock.patch.object(
        TangoClient, "_get_deviceproxy", return_value=Mock()
    ) as mock_obj:
        with mock.patch.object(
            TangoClient, "subscribe_attribute", side_effect=dummy_subscriber
        ):
            tango_client_obj = TangoClient("mid_csp/elt/master")
            device_proxy.TelescopeOn()
    assert device_proxy.telescopeHealthState == health_state


@pytest.fixture(scope="function")
def mock_sdp_master_proxy(mock_tango_server_helper, mock_tango_client):
    dut_properties = {"SdpMasterFQDN": "mid_sdp/elt/master"}
    event_subscription_map = {}
    Mock().subscribe_event.side_effect = lambda attr_name, event_type, callback, *args, **kwargs: event_subscription_map.update(
        {attr_name: callback}
    )
    with fake_tango_system(
        CentralNode, initial_dut_properties=dut_properties
    ) as tango_context:
        with mock.patch.object(
            TangoClient, "_get_deviceproxy", return_value=Mock()
        ) as mock_obj:
            tango_client_obj = TangoClient(dut_properties["SdpMasterFQDN"])
            yield tango_context.device, tango_client_obj, dut_properties[
                "SdpMasterFQDN"
            ], event_subscription_map


def test_telescope_health_state_is_ok_when_sdp_master_node_is_ok_after_start(
    mock_sdp_master_proxy, health_state, mock_tango_server_helper
):
    (
        device_proxy,
        tango_client_obj,
        csp_master_fqdn,
        event_subscription_map,
    ) = mock_sdp_master_proxy
    tango_server_obj = mock_tango_server_helper
    tango_server_obj.read_property.side_effect = Mock(return_value=["fqdn"])
    with mock.patch.object(
        TangoClient, "_get_deviceproxy", return_value=Mock()
    ) as mock_obj:
        with mock.patch.object(
            TangoClient, "subscribe_attribute", side_effect=dummy_subscriber
        ):
            tango_client_obj = TangoClient("mid_sdp/elt/master")
            device_proxy.TelescopeOn()
    assert device_proxy.telescopeHealthState == health_state


@pytest.fixture(scope="function")
def mock_subarraynode2_proxy(mock_tango_server_helper, mock_tango_client):
    dut_properties = {"subarray2_fqdn": "ska_mid/tm_subarray_node/2"}
    event_subscription_map = {}
    Mock().subscribe_event.side_effect = lambda attr_name, event_type, callback, *args, **kwargs: event_subscription_map.update(
        {attr_name: callback}
    )
    with fake_tango_system(
        CentralNode, initial_dut_properties=dut_properties
    ) as tango_context:
        with mock.patch.object(
            TangoClient, "_get_deviceproxy", return_value=Mock()
        ) as mock_obj:
            tango_client_obj = TangoClient(dut_properties["subarray2_fqdn"])
            yield tango_context.device, tango_client_obj, dut_properties[
                "subarray2_fqdn"
            ], event_subscription_map


def test_telescope_health_state_is_ok_when_subarray1_is_ok_after_start(
    mock_subarraynode_device, health_state
):
    (
        device_proxy,
        tango_client_obj,
        subarray1_fqdn,
        event_subscription_map,
        tango_server_obj,
    ) = mock_subarraynode_device
    tango_server_obj.read_property.side_effect = Mock(return_value=["fqdn"])
    tango_client_obj = TangoClient("ska_mid/tm_subarray_node/1")
    device_proxy.TelescopeOn()
    assert device_proxy.telescopeHealthState == health_state


def test_telescope_health_state_is_ok_when_subarray2_is_ok_after_start(
    mock_subarraynode2_proxy, health_state, mock_tango_server_helper
):
    (
        device_proxy,
        tango_client_obj,
        subarray2_fqdn,
        event_subscription_map,
    ) = mock_subarraynode2_proxy
    tango_server_obj = mock_tango_server_helper
    tango_server_obj.read_property.side_effect = Mock(return_value=["fqdn"])
    with mock.patch.object(
        TangoClient, "_get_deviceproxy", return_value=Mock()
    ) as mock_obj:
        with mock.patch.object(
            TangoClient, "subscribe_attribute", side_effect=dummy_subscriber
        ):
            tango_client_obj = TangoClient("ska_mid/tm_subarray_node/2")
            device_proxy.TelescopeOn()
    assert device_proxy.telescopeHealthState == health_state


@pytest.fixture(scope="function")
def mock_subarraynode3_proxy(mock_tango_server_helper, mock_tango_client):
    dut_properties = {"subarray3_fqdn": "ska_mid/tm_subarray_node/3"}
    event_subscription_map = {}
    Mock().subscribe_event.side_effect = lambda attr_name, event_type, callback, *args, **kwargs: event_subscription_map.update(
        {attr_name: callback}
    )
    with fake_tango_system(
        CentralNode, initial_dut_properties=dut_properties
    ) as tango_context:
        with mock.patch.object(
            TangoClient, "_get_deviceproxy", return_value=Mock()
        ) as mock_obj:
            tango_client_obj = TangoClient(dut_properties["subarray3_fqdn"])
            yield tango_context.device, tango_client_obj, dut_properties[
                "subarray3_fqdn"
            ], event_subscription_map


def test_telescope_health_state_is_ok_when_subarray3_is_ok_after_start(
    mock_subarraynode3_proxy, health_state, mock_tango_server_helper
):
    (
        device_proxy,
        tango_client_obj,
        subarray3_fqdn,
        event_subscription_map,
    ) = mock_subarraynode3_proxy
    tango_server_obj = mock_tango_server_helper
    tango_server_obj.read_property.side_effect = Mock(return_value=["fqdn"])
    with mock.patch.object(
        TangoClient, "_get_deviceproxy", return_value=Mock()
    ) as mock_obj:
        with mock.patch.object(
            TangoClient, "subscribe_attribute", side_effect=dummy_subscriber
        ):
            tango_client_obj = TangoClient("ska_mid/tm_subarray_node/3")
            device_proxy.TelescopeOn()
    assert device_proxy.telescopeHealthState == health_state


# Throw Devfailed exception for command with argument
def raise_devfailed_exception(*args):
    tango.Except.throw_exception(
        "CentralNode_Commandfailed",
        "This is error message for devfailed",
        " ",
        tango.ErrSeverity.ERR,
    )


def test_version_id():
    """Test for versionId"""
    with fake_tango_system(CentralNode) as tango_context:
        assert tango_context.device.versionId == release.version


def test_build_state():
    """Test for buildState"""
    with fake_tango_system(CentralNode) as tango_context:
        assert tango_context.device.buildState == (
            "{},{},{}".format(release.name, release.version, release.description)
        )


def any_method(with_name=None):
    class AnyMethod:
        def __eq__(self, other):
            if not isinstance(other, types.MethodType):
                return False
            return other.__func__.__name__ == with_name if with_name else True

    return AnyMethod()


@contextlib.contextmanager
def fake_tango_system(
    device_under_test,
    initial_dut_properties={},
    proxies_to_mock={},
    device_proxy_import_path="tango.DeviceProxy",
):
    with mock.patch(device_proxy_import_path) as patched_constructor:
        patched_constructor.side_effect = lambda device_fqdn: proxies_to_mock.get(
            device_fqdn, Mock()
        )
        patched_module = importlib.reload(sys.modules[device_under_test.__module__])
    device_under_test = getattr(patched_module, device_under_test.__name__)
    device_test_context = DeviceTestContext(
        device_under_test, properties=initial_dut_properties
    )
    device_test_context.start()
    yield device_test_context
    # device_test_context.stop()
