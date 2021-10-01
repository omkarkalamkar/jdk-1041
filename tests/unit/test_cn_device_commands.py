import pytest
import tango
import json
from tango.test_utils import DeviceTestContext
from ska_tmc_centralnode_mid.central_node import CentralNode
from ska_tmc_centralnode_mid.model.enum import ModesAvailability
from ska_tango_base.control_model import HealthState, TestMode, SimulationMode, ControlMode
from tango import DevState
from ska_tango_base.obs.obs_device import SKAObsDevice
from tests.helper_state_device import HelperStateDevice
from tests.helper_subarray_device import HelperSubArrayDevice
from tests.settings import DEVICE_LIST, SLEEP_TIME, TIMEOUT, logger, count_faulty_devices
from ska_tmc_centralnode_mid.dev_factory import DevFactory
from ska_tango_base.commands import ResultCode

@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": CentralNode,
            "devices": [
                {
                    "name": "ska_mid/tm_central/central_node",
                    "properties": {
                        "CspMasterLeafNodeFQDN": ["ska_mid/tm_leaf_node/csp_master"],
                        "CspMasterFQDN": ["mid_csp/elt/master"],
                        "SdpMasterLeafNodeFQDN": ["ska_mid/tm_leaf_node/sdp_master"],
                        "SdpMasterFQDN": ["mid_sdp/elt/master"],
                        "DishLeafNodePrefix": ["ska_mid/tm_leaf_node/d"],
                        "TMMidSubarrayNodes": ["ska_mid/tm_subarray_node/1"],
                        "TMMidCspSubarrayLeafNodes": ["ska_mid/tm_leaf_node/csp_subarray01"],
                        "TMMidSdpSubarrayLeafNodes": ["ska_mid/tm_leaf_node/sdp_subarray01"],
                        "NumDishes": [1]
                    },
                }
            ],
        },
        {
            "class": HelperSubArrayDevice,
            "devices": [
                {
                    "name": "ska_mid/tm_subarray_node/1"
                },
                {
                    "name": "ska_mid/tm_leaf_node/csp_subarray01"
                },
                {
                    "name": "ska_mid/tm_leaf_node/sdp_subarray01"
                }
            ],
        },
        {
            "class": HelperStateDevice,
            "devices": [
                {
                    "name": "ska_mid/tm_leaf_node/csp_master"
                },
                {
                    "name": "mid_csp/elt/master"
                },
                {
                    "name": "ska_mid/tm_leaf_node/sdp_master"
                },
                {
                    "name": "mid_sdp/elt/master"
                },
                {
                    "name": "mid_d0001/elt/master"
                },
                {
                    "name": "ska_mid/tm_leaf_node/d0001"
                }
            ]
        }
    )

@pytest.mark.xfail
def test_on_command(tango_context):
    # import debugpy; debugpy.debug_this_thread()
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device("ska_mid/tm_central/central_node")
    central_node.set_timeout_millis(300000)
    (result, _) = central_node.On()
    assert result == ResultCode.QUEUED



