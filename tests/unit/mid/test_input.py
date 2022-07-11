import pytest

from ska_tmc_centralnode.model.input import InputParameterMid


@pytest.mark.refactor_telescopeon
def test_properties():
    input = InputParameterMid(None)
    input.tm_subarray_dev_names = ("1", "2")
    assert input.tm_subarray_dev_names == ("1", "2")
    input.csp_subarray_dev_names = ("3", "4")
    assert input.csp_subarray_dev_names == ("3", "4")
    input.tm_dish_dev_names = "5"
    assert input.tm_dish_dev_names == ("5")
    input.dish_dev_names = "5"
    assert input.dish_dev_names == ("5")
    input.sdp_subarray_dev_names = "6"
    assert input.sdp_subarray_dev_names == ("6")
    input.csp_master_dev_name = "7"
    assert input.csp_master_dev_name == "7"
    input.sdp_master_dev_name = "8"
    assert input.sdp_master_dev_name == "8"
    input.tm_leaf_sdp_master_dev_name = "9"
    assert input.tm_leaf_sdp_master_dev_name == "9"
    input.tm_leaf_csp_master_dev_name = "10"
    assert input.tm_leaf_csp_master_dev_name == "10"
