"""This unit test is used for testing
aggregation using aggregation process
"""
import logging
import time
from datetime import datetime

import pytest
from ska_tango_base.control_model import HealthState

from ska_tmc_centralnode.manager.event_data_manager import (
    EventDataStorage,
    HealthStateData,
)


def generate_data(health_state_data_type):
    event_data = EventDataStorage(health_state_data_type)
    if health_state_data_type == "OK":
        event_data.health_state_data = {
            "csp/1": HealthStateData(
                health_state="OK", event_timestamp=datetime.now()
            ),
            "sdp/2": HealthStateData(
                health_state="OK", event_timestamp=datetime.now()
            ),
        }
    if health_state_data_type == "DEGRADED":
        event_data.health_state_data = {
            "csp/1": HealthStateData(
                health_state="DEGRADED", event_timestamp=datetime.now()
            ),
            "sdp/2": HealthStateData(
                health_state="DEGRADED", event_timestamp=datetime.now()
            ),
        }
    if health_state_data_type == "FAILED":
        event_data.health_state_data = {
            "csp/1": HealthStateData(
                health_state="FAILED", event_timestamp=datetime.now()
            ),
            "sdp/2": HealthStateData(
                health_state="FAILED", event_timestamp=datetime.now()
            ),
        }
    return event_data


@pytest.mark.aki2
def test_health_aggregation_process(
    aggregation_process_mid,
):
    """Test health state aggregation when data is added to the event data queue."""

    aggregation_process = aggregation_process_mid

    aggregation_process.start_aggregation_process()

    health_states_to_test = [
        ("OK", "OK"),
        ("DEGRADED", "DEGRADED"),
        ("FAILED", "FAILED"),
    ]

    for expected_state, test_state in health_states_to_test:
        logging.info(
            f"Testing health state: {test_state} and expected is {expected_state}"
        )
        event_data = generate_data(test_state)
        logging.info(f"My event data is  {event_data}")
        aggregation_process.event_data_queue.put(event_data)
        time.sleep(0.2)

        assert (
            aggregation_process.aggregated_health_state[0]
            == HealthState[expected_state]
        )

    aggregation_process.stop_aggregation_process()


@pytest.mark.parametrize(
    "telescope",
    ["mid", "low"],
)
def test_convert_event_data_to_dict(
    aggregation_process_mid, aggregation_process_low, telescope
):
    """This test convert event to dict method return dict as
    expected
    """
    if telescope == "mid":
        aggregation_process = aggregation_process_mid
    else:
        aggregation_process = aggregation_process_low

    event_data = EventDataStorage(
        health_state_data={
            "csp/1": HealthStateData(
                health_state="OK", event_timestamp=datetime.now()
            ),
            "sdp/2": HealthStateData(
                health_state="OK", event_timestamp=datetime.now()
            ),
        },
    )
    logging.info(f"my event data is {event_data}")
    event_data_dict = aggregation_process._convert_event_data_to_dict(
        event_data
    )
    expected_event_data_dict = {
        "all_unique_health_states": ["OK"],
    }

    logging.info(
        f"expected event dict {expected_event_data_dict} and {event_data_dict}"
    )
    assert all(
        v == event_data_dict[k] for k, v in expected_event_data_dict.items()
    ) and len(expected_event_data_dict) == len(event_data_dict)
