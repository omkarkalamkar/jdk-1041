import threading
from unittest.mock import Mock, patch

from ska_control_model import ResultCode
from ska_tango_base.faults import CommandError, ResultCodeError

from ska_tmc_centralnode.commands.central_node_command import (
    CentralNodeCommand,
)


def test_send_command_with_argin():
    cm = Mock()
    cc = CentralNodeCommand(cm)
    adapters = Mock()
    cc.invoke_commands_without_lrc = Mock()
    cc.send_command(adapters, "command failed", "testcommand", "argin")
    cc.invoke_commands_without_lrc.assert_called_once()


def test_error_message():
    cm = Mock()
    cc = CentralNodeCommand(cm)
    result, message = cc.adapter_error_message("test/device/1", "error")
    assert result == ResultCode.FAILED
    assert message == "Adapter creation failed for test/device/1: error"


@patch("ska_tmc_centralnode.commands.central_node_command.invoke_lrc")
def test_command_error(mock_invoke_lrc):
    cm = Mock()
    cc = CentralNodeCommand(cm)
    adapter = Mock()
    mock_invoke_lrc.side_effect = CommandError("command failed")
    result, message = cc.invoke_command_and_add_tracking_data(
        adapter, "Command"
    )
    assert result == ResultCode.REJECTED
    assert "command failed" in message
    mock_invoke_lrc.side_effect = ResultCodeError("command rejected")
    result, message = cc.invoke_command_and_add_tracking_data(
        adapter, "Command"
    )
    assert result == ResultCode.FAILED
    assert "command rejected" in message


def test_wait_for_completion():
    cm = Mock(
        command_timeout=5.0, command_completion_cond=threading.Condition()
    )
    cc = CentralNodeCommand(cm)
    cc.command_results["dummy_device"] = (ResultCode.FAILED, "error")
    result, message = cc.wait_for_command_completion(1)
    assert result == ResultCode.FAILED
    assert "error" in message
