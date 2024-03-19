from ska_tmc_centralnode.model.input import InputParameterMid


def test_properties():
    """Test for testing properties"""
    input = InputParameterMid(None)
    input.subarray_dev_names = ("1", "2")
    assert input.subarray_dev_names == ("1", "2")
    input.csp_subarray_dev_names = ("3", "4")
    assert input.csp_subarray_dev_names == ("3", "4")
    input.dish_leaf_node_dev_names = "5"
    assert input.dish_leaf_node_dev_names == ("5")
    input.dish_dev_names = "5"
    assert input.dish_dev_names == ("5")
    input.sdp_subarray_dev_names = "6"
    assert input.sdp_subarray_dev_names == ("6")
    input.csp_master_dev_name = "7"
    assert input.csp_master_dev_name == "7"
    input.sdp_master_dev_name = "8"
    assert input.sdp_master_dev_name == "8"
    input.sdp_mln_dev_name = "9"
    assert input.sdp_mln_dev_name == "9"
    input.csp_mln_dev_name = "10"
    assert input.csp_mln_dev_name == "10"
