# pylint: disable=unused-variable,W0612
# flake8: noqa
# Standard Python imports
import contextlib
import importlib
import json
import logging
import sys
import threading
import types
from os.path import dirname, join

import mock
import pytest

# Tango imports
import tango
from mock import MagicMock, Mock
from ska_tango_base.base import OpStateModel
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import (
    AdminMode,
    ControlMode,
    HealthState,
    LoggingLevel,
    ObsState,
    SimulationMode,
    TestMode,
)
from tango import DevState
from tango.test_context import DeviceTestContext
from tmc.common.tango_client import TangoClient
from tmc.common.tango_server_helper import TangoServerHelper

from ska_tmc_centralnode_mid import CentralNode, release
from ska_tmc_centralnode_mid.commands.telescope_on_command import TelescopeOn
from ska_tmc_centralnode_mid.commands.telescope_standby_command import (
    TelescopeStandby,
)
from ska_tmc_centralnode_mid.input_validator import AssignResourceValidator

assign_input_file = "command_AssignResources.json"
path = join(dirname(__file__), "data", assign_input_file)
with open(path, "r") as f:
    assign_input_str = f.read()

release_input_file = "command_ReleaseResources.json"
path = join(dirname(__file__), "data", release_input_file)
with open(path, "r") as f:
    release_input_str = f.read()


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


@pytest.fixture(scope="function")
def mock_update_resource_config_file():
    pass


# Discuss the aspect of Subarray returning response
# @pytest.mark.skip("will be reworked")
# @mock.patch(
#     "ska_tmc_centralnode_mid.commands.assign_resources_command.AssignResources.update_resource_config_file"
# )
# def test_assign_resources(mock_update_resource_config_file, mock_subarray):
#     device_proxy, tango_client_obj, tango_server_obj = mock_subarray
#     tango_server_obj.read_property.side_effect = Mock(
#         return_value=[
#             "ska_mid/tm_subarray_node/1",
#             "ska_mid/tm_subarray_node/2",
#             "ska_mid/tm_subarray_node/3",
#         ]
#     )
#     # mocking subarray device state as ON as per new state model
#     tango_client_obj.DevState = DevState.ON
#     receptor_ids_allocated = []
#     receptor_ids_allocated.append("0001")
#     dish = {}
#     dish["receptor_ids_allocated"] = receptor_ids_allocated
#     success_response = {}
#     success_response["dish"] = dish
#     tango_client_obj.deviceproxy.command_inout.side_effect = (
#         mock_subarray_call_assign_resources_success
#     )
#     message = device_proxy.AssignResources(assign_input_str)
#     assert json.loads(message) == success_response


# Need to emplement excpetion block and unit test
# #     """Negative Test for StowAntennas"""
# @pytest.mark.skip("will be reworked")
# def test_stow_antennas_invalid_value(
#     mock_tango_server_helper, mock_tango_client
# ):
#     tango_server_obj = mock_tango_server_helper
#     tango_server_obj.read_property.side_effect = Mock(return_value=["fqdn"])
#     with fake_tango_system(CentralNode) as tango_context:
#         argin = [
#             "invalid_antenna",
#         ]
#         with pytest.raises(tango.DevFailed) as df:
#             tango_context.device.StowAntennas(argin)

#         assert const.ERR_STOW_ARGIN in str(df.value)

# Covered in integration tests
# @pytest.mark.skip("will be reworked")
# def test_release_resources(mock_subarray):
#     device_proxy, tango_client_obj, _ = mock_subarray
#     release_all_success = {"release_all": True, "receptor_ids": []}
#     tango_client_obj.deviceproxy.command_inout.side_effect = (
#         mock_subarray_call_release_resources_success
#     )
#     message = device_proxy.ReleaseResources(release_input_str)
#     assert json.dumps(release_all_success) in message


@contextlib.contextmanager
def fake_tango_system(
    device_under_test,
    initial_dut_properties={},
    proxies_to_mock={},
    device_proxy_import_path="tango.DeviceProxy",
):
    with mock.patch(device_proxy_import_path) as patched_constructor:
        patched_constructor.side_effect = (
            lambda device_fqdn: proxies_to_mock.get(device_fqdn, Mock())
        )
        patched_module = importlib.reload(
            sys.modules[device_under_test.__module__]
        )
    device_under_test = getattr(patched_module, device_under_test.__name__)
    device_test_context = DeviceTestContext(
        device_under_test, properties=initial_dut_properties
    )
    device_test_context.start()
    yield device_test_context
    # device_test_context.stop()
