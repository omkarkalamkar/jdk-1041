import pytest

from ska_tmc_centralnode.model.input import InputParameterLow


@pytest.mark.SKA_low
def test_properties():
    input = InputParameterLow(None)
    input.subarray_dev_names = ("1", "2")
    assert input.subarray_dev_names == ("1", "2")
    # input.mccs_mln_dev_name = "leaf node"
    # assert input.mccs_mln_dev_name == "leaf node"
    # input.mccs_master_dev_name = "master node"
    # assert input.mccs_master_dev_name == "master node"
    input.csp_subarray_dev_names = ("3", "4")
    assert input.csp_subarray_dev_names == ("3", "4")
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
