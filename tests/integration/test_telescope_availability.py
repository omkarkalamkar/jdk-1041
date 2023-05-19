# import time

# import pytest
# import tango
# from ska_tmc_common.dev_factory import DevFactory

# from tests.settings import (
#     MID_CSP_MLN_DEVICE,
#     MID_SDP_MLN_DEVICE,
#     MID_SUBARRAY_DEVICE,
#     logger,
# )


# @pytest.mark.ava
# @pytest.mark.post_deployment
# @pytest.mark.SKA_mid
# def test_telescope_availability(tango_context, change_event_callbacks):
#     dev_factory = DevFactory()
#     central_node = dev_factory.get_device("ska_mid/tm_central/central_node")
#     csp_mln = dev_factory.get_device(MID_CSP_MLN_DEVICE)
#     sdp_mln = dev_factory.get_device(MID_SDP_MLN_DEVICE)
#     subarray_node = dev_factory.get_device(MID_SUBARRAY_DEVICE)
#     # central_node.subscribe_event(
#     #     "telescopeAvailability",
#     #     tango.EventType.CHANGE_EVENT,
#     #     change_event_callbacks["telescopeAvailability"],
#     # )
#     subarray_node.SetIsSubarrayAvailable(True)
#     csp_mln.SetisSubsystemAvailable(True)
#     sdp_mln.SetisSubsystemAvailable(True)

#     # attr_value = central_node.read_attribute("telescopeAvailability").value
#     # logger.info(f"Availability attribute: {attr_value}")

#     # attr_value = central_node.read_attribute("telescopeAvailability").value
#     # logger.info(f"Availability attribute: {attr_value}")
#     # time.sleep(2)

#     # subarray_node.SetIsSubarrayAvailable(False)
#     # attr_value = central_node.read_attribute("telescopeAvailability").value
#     # logger.info(f"Availability attribute: {attr_value}")
#     # time.sleep(2)

#     # subarray_node.SetIsSubarrayAvailable(True)
#     # attr_value = central_node.read_attribute("telescopeAvailability")
#     # logger.info(f"Availability attribute: {attr_value}")
#     # time.sleep(2)
