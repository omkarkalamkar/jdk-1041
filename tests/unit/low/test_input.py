import pytest

from ska_tmc_centralnode.model.input import InputParameterLow


@pytest.mark.long_running
def test_properties():
    input = InputParameterLow(None)
    input.tm_subarray_dev_names = ("1", "2")
    assert input.tm_subarray_dev_names == ("1", "2")
    input.mccs_master_leaf_node = "leaf node"
    assert input.mccs_master_leaf_node == "leaf node"
    input.mccs_master_dev_name = "master node"
    assert input.mccs_master_dev_name == "master node"
