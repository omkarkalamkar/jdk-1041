"""Test cases for reset command"""
import pytest
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory

from ska_tmc_centralnode.utils.constants import (
    CENTRALNODE_LOW,
    CENTRALNODE_MID,
)


def reset_command(central_node_fqdn):
    """Method for reset command"""
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_fqdn)
    result_code, message = central_node.Reset()
    assert result_code == ResultCode.REJECTED
    assert message == ["Reset command is not implemented"]


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_reset_command_mid():
    """test reset command for mid"""
    reset_command(CENTRALNODE_MID)


@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_reset_command_low():
    """Tests reset command for low"""
    reset_command(CENTRALNODE_LOW)
