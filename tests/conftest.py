"""Conftest test case file for unit testing"""

# pylint: disable=unused-argument
# pylint: disable=redefined-outer-name
import logging
from multiprocessing import Manager
from os.path import dirname, join

import mock
import pytest
import tango
from ska_control_model import AdminMode
from ska_tango_testing.mock import MockCallable
from ska_tango_testing.mock.tango.event_callback import (
    MockTangoEventCallbackGroup,
)
from ska_tmc_common import HelperMCCSController, HelperMCCSMasterLeafNode
from ska_tmc_common.dev_factory import DevFactory
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
from tango.test_context import MultiDeviceTestContext

from ska_tmc_centralnode.manager.aggregate_process import (
    HealthStateAggregationProcessor,
)
from tests.common_utils import wait_and_validate_device_attribute_value
from tests.helpers.cn_helper_subarray_device import CNHelperSubArrayDevice
from tests.settings import (
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    LOW_CSP_MASTER_DEVICE,
    LOW_CSP_MLN_DEVICE,
    LOW_CSP_SLN_DEVICE,
    LOW_SDP_MASTER_DEVICE,
    LOW_SDP_MLN_DEVICE,
    LOW_SDP_SLN_DEVICE,
    LOW_SUBARRAY_DEVICE,
    MCCS_CONTROLLER,
    MCCS_MLN_DEVICE,
    MID_CENTRAL_NODE,
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
            ],
        },
        {
            "class": HelperDishLNDevice,
            "devices": [
                {"name": DISH_LEAF_NODE_DEVICE},
            ],
        },
    )


def pytest_sessionstart(session):
    """
    Pytest hook; prints info about tango version.
    :param session: a pytest Session object
    :type session: :py:class:`pytest.Session`
    """
    print(tango.utils.info())


def pytest_addoption(parser):
    """
    Pytest hook; implemented to add the `--true-context` option, used to
    indicate that a true Tango subsystem is available, so there is no
    need for a :py:class:`tango.test_context.MultiDeviceTestContext`.
    :param parser: the command line options parser
    :type parser: :py:class:`argparse.ArgumentParser`
    """
    parser.addoption(
        "--true-context",
        action="store_true",
        default=False,
        help=(
            "Tell pytest that you have a true Tango context and don't "
            "need to spin up a Tango test context"
        ),
    )


@pytest.fixture
def tango_context(devices_to_load, request):
    """Tango context fixture"""
    true_context = request.config.getoption("--true-context")
    logging.info("true context: %s", true_context)
    if not true_context:
        with MultiDeviceTestContext(
            devices_to_load, process=True, timeout=50
        ) as context:
            DevFactory._test_context = context
            logging.info("test context set")
            yield context
    else:
        yield None


@pytest.fixture
def task_callback() -> MockCallable:
    """Creates a mock callable for asynchronous testing

    :rtype: MockCallable
    """
    task_callback = MockCallable(15)
    return task_callback


@pytest.fixture
def change_event_callbacks() -> MockTangoEventCallbackGroup:
    """
    Return a dictionary of Tango device change event callbacks \
        with asynchrony support.

    :return: a collections.defaultdict that returns change event
        callbacks by name.
    """
    return MockTangoEventCallbackGroup(
        "longRunningCommandStatus",
        "longRunningCommandsInQueue",
        "longRunningCommandResult",
        "State",
        "telescopeState",
        "telescopeHealthState",
        "tmOpState",
        "lastDeviceInfoChanged",
        "sourceDishVccConfig",
        "dishMode",
        "pointingState",
        "DishVccMapValidationResult",
        "healthState",
        "isDishVccConfigSet",
        "DishVccValidationStatus",
        "DishVccCommandStatus",
        timeout=50.0,
    )


def get_input_str(path):
    """
    Returns input json string
    :rtype: String
    """
    with open(path, "r", encoding="utf-8") as f:
        input_arg = f.read()
    return input_arg


@pytest.fixture()
def json_factory():
    """
    Json factory for getting json files
    """

    def _get_json(slug):
        return get_input_str(join(dirname(__file__), "data", f"{slug}.json"))

    return _get_json


@pytest.fixture
def set_mid_sdp_csp_mln_availability_for_aggregation():
    """
    Setting mid Csp subarray leaf node and Sdp subarray leaf node availabilty
    attribute isSubsystemAvailable as True for aggregation
    """
    dev_factory = DevFactory()
    proxy_csp_mln = dev_factory.get_device(MID_CSP_MLN_DEVICE)
    proxy_csp_mln.SetSubsystemAvailable(True)

    proxy_sdp_mln = dev_factory.get_device(MID_SDP_MLN_DEVICE)
    proxy_sdp_mln.SetSubsystemAvailable(True)

    logging.debug(
        "CspSubarrayLeafNode availability is: %s",
        proxy_csp_mln.isSubsystemAvailable,
    )
    logging.debug(
        "SdpSubarrayLeafNode availability is: %s",
        proxy_sdp_mln.isSubsystemAvailable,
    )


@pytest.fixture
def set_low_devices_availability_for_aggregation():
    """
    Setting low Csp subarray leaf node and Sdp subarray leaf node availabilty
    attribute isSubsystemAvailable as True for aggregation
    """
    dev_factory = DevFactory()
    proxy_csp_mln = dev_factory.get_device(LOW_CSP_MLN_DEVICE)
    proxy_csp_mln.SetSubsystemAvailable(True)

    proxy_sdp_mln = dev_factory.get_device(LOW_SDP_MLN_DEVICE)
    proxy_sdp_mln.SetSubsystemAvailable(True)

    proxy_mccs_mln = dev_factory.get_device(MCCS_MLN_DEVICE)
    proxy_mccs_mln.SetSubsystemAvailable(True)

    logging.debug(
        "CspSubarrayLeafNode availability is: %s",
        proxy_csp_mln.isSubsystemAvailable,
    )
    logging.debug(
        "SdpSubarrayLeafNode availability is: %s",
        proxy_sdp_mln.isSubsystemAvailable,
    )
    logging.debug(
        "MccsSubarrayLeafNode availability is: %s",
        proxy_mccs_mln.isSubsystemAvailable,
    )


@pytest.fixture(scope="session", autouse=True)
def is_dish_vcc_set(request):
    """Validate dish vcc config set"""
    marker = request.node.get_closest_marker("SKA_mid")
    logging.debug("Checking Dish Config set or not for marker %s", marker)
    if marker:
        dev_factory = DevFactory()
        assert wait_and_validate_device_attribute_value(
            dev_factory.get_device(MID_CENTRAL_NODE),
            "isDishVccConfigSet",
            True,
        ), "Timeout while waiting for validating attribute value"


@pytest.fixture
def aggregation_process_mid():
    """Create aggregation process mid object"""
    process_manager = Manager()
    event_queue = process_manager.Queue()
    aggregated_health_state = process_manager.list([""])
    mock_obj = mock.Mock()

    aggregation_process = HealthStateAggregationProcessor(
        event_queue, aggregated_health_state, mock_obj
    )

    yield aggregation_process

    aggregation_process.stop_aggregation_process()
    process_manager.shutdown()


@pytest.fixture
def aggregation_process_low():
    """Create aggregation process low object"""
    process_manager = Manager()
    event_queue = process_manager.Queue()
    aggregated_health_state = process_manager.list([""])
    mock_obj = mock.Mock()
    aggregation_process = HealthStateAggregationProcessor(
        event_queue, aggregated_health_state, mock_obj
    )

    yield aggregation_process
    aggregation_process.stop_aggregation_process()
    process_manager.shutdown()


@pytest.fixture
def set_mid_sdp_csp_admin_modes():
    """
    Setting mid Csp controller and Sdp controller adminModes
    attribute as Online.
    """
    dev_factory = DevFactory()
    proxy_csp_mln = dev_factory.get_device(MID_CSP_MLN_DEVICE)
    proxy_csp_mln.SetCspControllerAdminMode(AdminMode.ONLINE)

    proxy_sdp_mln = dev_factory.get_device(MID_SDP_MLN_DEVICE)
    proxy_sdp_mln.SetSdpControllerAdminMode(AdminMode.ONLINE)

    logging.debug(
        "CspControllerAdminMode attrubte is: %s",
        proxy_csp_mln.cspControllerAdminMode,
    )
    logging.debug(
        "SdpControllerAdminMode attrubte is: %s",
        proxy_sdp_mln.sdpControllerAdminMode,
    )


@pytest.fixture
def set_low_sdp_csp_mccs_admin_modes():
    """
    Setting low Csp controller and Sdp controller and Mccs controller
    adminModes attribute as Online.
    """
    dev_factory = DevFactory()
    proxy_csp_mln = dev_factory.get_device(LOW_CSP_MLN_DEVICE)
    proxy_csp_mln.SetCspControllerAdminMode(AdminMode.ONLINE)

    proxy_sdp_mln = dev_factory.get_device(LOW_SDP_MLN_DEVICE)
    proxy_sdp_mln.SetSdpControllerAdminMode(AdminMode.ONLINE)

    proxy_mccs_mln = dev_factory.get_device(MCCS_MLN_DEVICE)
    proxy_mccs_mln.SetMccsControllerAdminMode(AdminMode.ONLINE)
    logging.debug(
        "cspControllerAdminMode attrubte is: %s",
        proxy_csp_mln.cspControllerAdminMode,
    )
    logging.debug(
        "sdpControllerAdminMode attrubte is: %s",
        proxy_sdp_mln.sdpControllerAdminMode,
    )

    logging.debug(
        "mccsControllerAdminMode attrubte is: %s",
        proxy_mccs_mln.mccsControllerAdminMode,
    )
