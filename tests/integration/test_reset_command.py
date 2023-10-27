import pytest
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory


def reset_command(central_node_fqdn):
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_fqdn)
    result_code, message = central_node.Reset()
    assert result_code == ResultCode.REJECTED
    assert message == ["Reset command is not implemented"]


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_reset_command_mid():
    reset_command("ska_mid/tm_central/central_node")


@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_reset_command_low():
    reset_command("ska_mid/tm_central/central_node")
