import pytest
from mock import MagicMock
from ska_tmc_common import AdapterFactory
from ska_tmc_simulators import HelperMCCSController, HelperMCCSMasterLeafNode
from ska_tmc_simulators.cn_helper_subarray_device import CNHelperSubArrayDevice
from ska_tmc_simulators.helper_base_device import HelperBaseDevice
from ska_tmc_simulators.helper_csp_master_leaf_node import (
    HelperCspMasterLeafDevice,
)
from ska_tmc_simulators.helper_dish_device import (
    HelperDishDevice,
    HelperDishLNDevice,
)
from ska_tmc_simulators.helper_sdp_master_leaf_node import (
    HelperSDPMasterLeafNode,
)
from ska_tmc_simulators.helper_subarray_leaf_device import (
    HelperSubarrayLeafDevice,
)

from ska_tmc_centralnode.refactored_commands.load_dish_cfg.contexts import (
    DeviceContext,
    LoadDishCfgCommandContext,
    LoadDishCfgRuntimeContext,
)
from tests.settings import (
    DISH_LEAF_NODE_DEVICE,
    DISH_LEAF_NODE_DEVICE_099,
    DISH_LEAF_NODE_DEVICE_500,
    DISH_LEAF_NODE_DEVICE_999,
    DISH_MASTER_DEVICE,
    DISH_MASTER_DEVICE_099,
    DISH_MASTER_DEVICE_500,
    DISH_MASTER_DEVICE_999,
    LOW_CSP_MASTER_DEVICE,
    LOW_CSP_MLN_DEVICE,
    LOW_CSP_SLN_DEVICE,
    LOW_SDP_MASTER_DEVICE,
    LOW_SDP_MLN_DEVICE,
    LOW_SDP_SLN_DEVICE,
    LOW_SUBARRAY_DEVICE,
    MCCS_CONTROLLER,
    MCCS_MLN_DEVICE,
    MID_CSP_MASTER_DEVICE,
    MID_CSP_MLN_DEVICE,
    MID_CSP_SLN_DEVICE,
    MID_SDP_MASTER_DEVICE,
    MID_SDP_MLN_DEVICE,
    MID_SDP_SLN_DEVICE,
    MID_SUBARRAY_DEVICE,
)


@pytest.fixture()
def devices_to_load():
    """Devices to load for command invocation."""
    return (
        {
            "class": CNHelperSubArrayDevice,
            "devices": [
                {"name": LOW_SUBARRAY_DEVICE},
                {"name": MID_SUBARRAY_DEVICE},
            ],
        },
        {
            "class": HelperMCCSMasterLeafNode,
            "devices": [
                {"name": MCCS_MLN_DEVICE},
            ],
        },
        {
            "class": HelperMCCSController,
            "devices": [
                {"name": MCCS_CONTROLLER},
            ],
        },
        {
            "class": HelperSubarrayLeafDevice,
            "devices": [
                {"name": LOW_CSP_SLN_DEVICE},
                {"name": LOW_SDP_SLN_DEVICE},
                {"name": MID_CSP_SLN_DEVICE},
                {"name": MID_SDP_SLN_DEVICE},
            ],
        },
        {
            "class": HelperCspMasterLeafDevice,
            "devices": [
                {"name": LOW_CSP_MLN_DEVICE},
                {"name": MID_CSP_MLN_DEVICE},
            ],
        },
        {
            "class": HelperBaseDevice,
            "devices": [
                {"name": LOW_CSP_MASTER_DEVICE},
                {"name": LOW_SDP_MASTER_DEVICE},
                {"name": MID_CSP_MASTER_DEVICE},
                {"name": MID_SDP_MASTER_DEVICE},
            ],
        },
        {
            "class": HelperSDPMasterLeafNode,
            "devices": [
                {"name": MID_SDP_MLN_DEVICE},
                {"name": LOW_SDP_MLN_DEVICE},
            ],
        },
        {
            "class": HelperDishDevice,
            "devices": [
                {"name": DISH_MASTER_DEVICE},
                {"name": DISH_MASTER_DEVICE_999},
                {"name": DISH_MASTER_DEVICE_500},
                {"name": DISH_MASTER_DEVICE_099},
            ],
        },
        {
            "class": HelperDishLNDevice,
            "devices": [
                {"name": DISH_LEAF_NODE_DEVICE},
                {"name": DISH_LEAF_NODE_DEVICE_099},
                {"name": DISH_LEAF_NODE_DEVICE_500},
                {"name": DISH_LEAF_NODE_DEVICE_999},
            ],
        },
    )


def _get_mock_dishln_name(instance: str) -> str:
    """Provides the dish ln name based on instance name."""
    return "mid-dish/dish-leaf-node/" + instance


@pytest.fixture
def device_context():
    """Create DeviceContext for LoadDishCfg tests."""

    context = MagicMock(spec=DeviceContext)

    context.csp_mln_device_name = "mid-csp/master-leaf-node/0001"

    context.dish_leaf_node_dev_names = [
        _get_mock_dishln_name("001"),
        _get_mock_dishln_name("002"),
    ]

    context.get_dev = MagicMock()

    return context


@pytest.fixture
def command_context():
    """Create CommandContext for LoadDishCfg tests."""

    context = MagicMock(spec=LoadDishCfgCommandContext)

    context.update_command_in_progress_id = MagicMock()

    context.set_load_dish_cfg_aggregated_result = MagicMock()

    context.set_dish_vcc_command_status = MagicMock()

    context.update_dish_vcc_flag = MagicMock()

    context.append_dish_dev_names = MagicMock()

    context.update_kval_aggregator = MagicMock()

    return context


@pytest.fixture
def configure_runtime_context(
    device_context,
    command_context,
):
    """Create LoadDishCfg runtime context."""

    runtime_context = MagicMock(spec=LoadDishCfgRuntimeContext)

    runtime_context.device_ctx = device_context
    runtime_context.command_ctx = command_context

    runtime_context.dish_kvalue_validation_aggregator = MagicMock()

    runtime_context.dish_kvalue_validation_aggregator.dln_kvalue_validation_results = (
        {}
    )

    runtime_context.update_kval_aggregator = MagicMock()

    runtime_context.append_dish_dev_names = MagicMock()

    return runtime_context


@pytest.fixture
def adapter_factory():
    """Create mocked adapter factory."""

    factory = MagicMock(spec=AdapterFactory)

    factory.get_or_create_adapter = MagicMock()

    return factory


@pytest.fixture
def dish_adapter():
    """Create a mocked dish adapter."""

    adapter = MagicMock()

    adapter.dev_name = _get_mock_dishln_name("001")

    adapter.proxy = MagicMock()

    return adapter


@pytest.fixture
def dish_adapters():
    """Create multiple mocked dish adapters."""

    adapter_1 = MagicMock()
    adapter_1.dev_name = _get_mock_dishln_name("001")

    adapter_2 = MagicMock()
    adapter_2.dev_name = _get_mock_dishln_name("002")

    return [adapter_1, adapter_2]
