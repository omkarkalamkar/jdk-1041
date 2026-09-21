"""Test cases file"""

from ska_tmc_centralnode.model.input import InputParameterMid


def test_properties():
    """Test for testing properties"""
    input_param = InputParameterMid(None)
    input_param.subarray_dev_names = ("1", "2")
    assert input_param.subarray_dev_names == ("1", "2")
    input_param.csp_subarray_dev_names = ("3", "4")
    assert input_param.csp_subarray_dev_names == ("3", "4")
    input_param.dish_leaf_node_dev_names = "5"
    assert input_param.dish_leaf_node_dev_names == ("5")
    input_param.dish_dev_names = "5"
    assert input_param.dish_dev_names == ("5")
    input_param.sdp_subarray_dev_names = "6"
    assert input_param.sdp_subarray_dev_names == ("6")
    input_param.csp_master_dev_name = "7"
    assert input_param.csp_master_dev_name == "7"
    input_param.sdp_master_dev_name = "8"
    assert input_param.sdp_master_dev_name == "8"
    input_param.sdp_mln_dev_name = "9"
    assert input_param.sdp_mln_dev_name == "9"
    input_param.csp_mln_dev_name = "10"
    assert input_param.csp_mln_dev_name == "10"
