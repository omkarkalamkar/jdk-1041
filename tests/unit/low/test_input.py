"""Test case module"""


from unittest.mock import Mock

from ska_tmc_centralnode.model.input import InputParameterLow


def test_properties():
    """Test properties for telescope low."""
    changed_callback = Mock()
    input = InputParameterLow(changed_callback)
    input.subarray_dev_names = ("1", "2")
    changed_callback.assert_called()
    assert input.subarray_dev_names == ("1", "2")
    input.mccs_mln_dev_name = "leaf node"
    changed_callback.assert_called()
    assert input.mccs_mln_dev_name == "leaf node"
    input.mccs_master_dev_name = "master node"
    changed_callback.assert_called()
    assert input.mccs_master_dev_name == "master node"
    input.csp_subarray_dev_names = ("3", "4")
    changed_callback.assert_called()
    assert input.csp_subarray_dev_names == ("3", "4")
    input.sdp_subarray_dev_names = "6"
    changed_callback.assert_called()
    assert input.sdp_subarray_dev_names == ("6")
    input.csp_master_dev_name = "7"
    changed_callback.assert_called()
    assert input.csp_master_dev_name == "7"
    input.sdp_master_dev_name = "8"
    changed_callback.assert_called()
    assert input.sdp_master_dev_name == "8"
    input.sdp_mln_dev_name = "9"
    changed_callback.assert_called()
    assert input.sdp_mln_dev_name == "9"
    input.csp_mln_dev_name = "10"
    changed_callback.assert_called()
    assert input.csp_mln_dev_name == "10"
