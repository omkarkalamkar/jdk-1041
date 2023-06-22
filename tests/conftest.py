# pylint: disable=unused-argument
import json
import logging
from os.path import dirname, join

import pytest
import tango
from ska_tango_testing.mock import MockCallable
from ska_tango_testing.mock.tango.event_callback import (
    MockTangoEventCallbackGroup,
)
from ska_tmc_common.dev_factory import DevFactory
from tango.test_context import MultiDeviceTestContext

from tests.settings import (
    LOW_CSP_MLN_DEVICE,
    LOW_SDP_MLN_DEVICE,
    MID_CSP_MLN_DEVICE,
    MID_SDP_MLN_DEVICE,
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
    true_context = request.config.getoption("--true-context")
    logging.info("true context: %s", true_context)
    if not true_context:
        with MultiDeviceTestContext(devices_to_load, process=False) as context:
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
    task_callback = MockCallable(5)
    return task_callback


@pytest.fixture
def change_event_callbacks() -> MockTangoEventCallbackGroup:
    """
    Return a dictionary of Tango device change event callbacks with asynchrony support.

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
        timeout=30.0,
    )


def get_input_str(path):
    """
    Returns input json string
    :rtype: String
    """
    with open(path, "r") as f:
        input_arg = json.load(f)
    return json.dumps(input_arg)


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
    proxy_csp_mln.SetisSubsystemAvailable(True)

    proxy_sdp_mln = dev_factory.get_device(MID_SDP_MLN_DEVICE)
    proxy_sdp_mln.SetisSubsystemAvailable(True)

    logging.debug(
        "CspSubarrayLeafNode availability is: %s",
        proxy_csp_mln.isSubsystemAvailable,
    )
    logging.debug(
        "SdpSubarrayLeafNode availability is: %s",
        proxy_sdp_mln.isSubsystemAvailable,
    )


@pytest.fixture
def set_low_sdp_csp_mln_availability_for_aggregation():
    """
    Setting low Csp subarray leaf node and Sdp subarray leaf node availabilty
    attribute isSubsystemAvailable as True for aggregation
    """
    dev_factory = DevFactory()
    proxy_csp_mln = dev_factory.get_device(LOW_CSP_MLN_DEVICE)
    proxy_csp_mln.SetisSubsystemAvailable(True)

    proxy_sdp_mln = dev_factory.get_device(LOW_SDP_MLN_DEVICE)
    proxy_sdp_mln.SetisSubsystemAvailable(True)

    logging.debug(
        "CspSubarrayLeafNode availability is: %s",
        proxy_csp_mln.isSubsystemAvailable,
    )
    logging.debug(
        "SdpSubarrayLeafNode availability is: %s",
        proxy_sdp_mln.isSubsystemAvailable,
    )
