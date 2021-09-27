from ska_tango_base.commands import ResultCode
from tests.settings import  logger
from ska_tmc_centralnode_mid.commands.on_command import On
from mock.mock import Mock
from ska_tmc_centralnode_mid.manager.adapters import BaseAdapter
from ska_tmc_centralnode_mid.manager.component_manager import CNComponentManager
from ska_tmc_centralnode_mid.model.op_state_model import TMCOpStateModel

def test_on_command():
    op_state_model = TMCOpStateModel(logger)
    cm = CNComponentManager(op_state_model, logger=logger, _monitoring_loop=True, _event_receiver=True)
    proxy = Mock()
    adapter = BaseAdapter("ska_mid/tm_leaf_node/csp_master", proxy)
    cm.add_adapter(adapter)
    on_command = On(cm)
    (result_code, _) = on_command.do()
    assert result_code == ResultCode.OK
    proxy.On.assert_called()
