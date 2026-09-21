"""Test case module"""


from unittest.mock import Mock

from ska_tmc_centralnode.model.input import InputParameterLow


def test_properties():
    """Test properties for telescope low."""
    changed_callback = Mock()
    input_param = InputParameterLow(changed_callback)
    input_param.subarray_dev_names = ("1", "2")
    changed_callback.assert_called()
    assert input_param.subarray_dev_names == ("1", "2")
    input_param.mccs_mln_dev_name = "leaf node"
    changed_callback.assert_called()
    assert input_param.mccs_mln_dev_name == "leaf node"
    input_param.mccs_master_dev_name = "master node"
    changed_callback.assert_called()
    assert input_param.mccs_master_dev_name == "master node"
    input_param.csp_subarray_dev_names = ("3", "4")
    changed_callback.assert_called()
    assert input_param.csp_subarray_dev_names == ("3", "4")
    input_param.sdp_subarray_dev_names = "6"
    changed_callback.assert_called()
    assert input_param.sdp_subarray_dev_names == ("6")
    input_param.csp_master_dev_name = "7"
    changed_callback.assert_called()
    assert input_param.csp_master_dev_name == "7"
    input_param.sdp_master_dev_name = "8"
    changed_callback.assert_called()
    assert input_param.sdp_master_dev_name == "8"
    input_param.sdp_mln_dev_name = "9"
    changed_callback.assert_called()
    assert input_param.sdp_mln_dev_name == "9"
    input_param.csp_mln_dev_name = "10"
    changed_callback.assert_called()
    assert input_param.csp_mln_dev_name == "10"
