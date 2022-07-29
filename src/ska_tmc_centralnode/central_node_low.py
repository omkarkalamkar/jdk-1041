"""
Central Node is a coordinator of the complete M&C system.
Central Node implements the standard set
of state and mode attributes defined by the SKA Control Model.
"""
from ska_tango_base.commands import ResultCode, SubmittedSlowCommand
from ska_tmc_common.op_state_model import TMCOpStateModel
from tango import AttrWriteType
from tango.server import attribute, device_property, run

from ska_tmc_centralnode.central_node import AbstractCentralNode
from ska_tmc_centralnode.manager.component_manager import CNComponentManager
from ska_tmc_centralnode.model.input import InputParameterLow

__all__ = ["CentralNodeLow", "main"]


class CentralNodeLow(AbstractCentralNode):
    """
    Central Node is a coordinator of the complete Telescope system

    """

    # -----------------
    # Device Properties
    # -----------------
    MCCSMasterLeafNodeFQDN = device_property(dtype="str")

    MCCSSubarrayLeafNodeFQDN = device_property(dtype="str")

    MCCSMasterNodeFQDN = device_property(dtype="str")
    # ----------
    # Attributes
    # ----------

    mccsMasterLeafNodeName = attribute(
        dtype="DevString",
        access=AttrWriteType.READ_WRITE,
    )

    mccsSubarrayLeafNodeName = attribute(
        dtype="DevString",
        access=AttrWriteType.READ_WRITE,
    )

    mccsMasterNodeName = attribute(
        dtype="DevString",
        access=AttrWriteType.READ_WRITE,
    )

    # ---------------
    # General methods
    # ---------------
    class InitCommand(AbstractCentralNode.InitCommand):
        """
        A class for the TMC CentralNode's init_device() method.
        """

        def do(self):
            """
            Initializes the attributes and properties of the Central Node.

            :return: A tuple containing a return code and a string message indicating status.
             The message is for information purpose only.

            :rtype: (ReturnCode, str)
            """
            super().do()

            return (ResultCode.OK, "")

    # ------------------
    # Attributes methods
    # ------------------

    def read_mccsMasterLeafNodeName(self):
        """Return the mccsmasterleafnodename attribute."""
        return self.component_manager.input_parameter.mccs_master_leaf_node

    def write_mccsMasterLeafNodeName(self, value):
        """Set the mccsmasterleafnodename attribute."""
        self.component_manager.input_parameter.mccs_master_leaf_node = value
        self.component_manager.update_input_parameter()

    def read_mccsSubarrayLeafNodeName(self):
        """Return the mccsSubarrayLeafNodeName attribute."""
        return self.component_manager.input_parameter.mccs_subarray_leaf_node

    def write_mccsSubarrayLeafNodeName(self, value):
        """Set the mccsSubarrayLeafNodeName attribute."""
        self.component_manager.input_parameter.mccs_subarray_leaf_node = value
        self.component_manager.update_input_parameter()

    def read_mccsMasterNodeName(self):
        """Return the mccsMasterNodeName attribute."""
        return self.component_manager.input_parameter.mccs_master_dev_name

    def write_mccsMasterNodeName(self, value):
        """Set the mccsMasterNodeName attribute."""
        self.component_manager.input_parameter.mccs_master_dev_name = value
        self.component_manager.update_input_parameter()

    def create_component_manager(self):
        self.op_state_model = TMCOpStateModel(
            logger=self.logger, callback=super()._update_state
        )
        cm = CNComponentManager(
            self.op_state_model,
            logger=self.logger,
            _update_device_callback=self.update_device_callback,
            _update_telescope_state_callback=self.update_telescope_state_callback,
            _update_telescope_health_state_callback=self.update_telescope_health_state_callback,
            _update_tmc_op_state_callback=self.update_tmc_op_state_callback,
            _update_imaging_callback=None,
            communication_state_changed_callback=None,
            component_state_changed_callback=None,
            max_workers=self.MaxWorker,
            proxy_timeout=self.ProxyTimeout,
            _input_parameter=InputParameterLow(None),
            sleep_time=self.SleepTime,
        )
        cm.input_parameter.tm_subarray_dev_names = self.TMSubarrayNodes
        cm.input_parameter.mccs_master_leaf_node = (
            self.MCCSMasterLeafNodeFQDN or ""
        )
        cm.input_parameter.mccs_subarray_leaf_node = (
            self.MCCSSubarrayLeafNodeFQDN or ""
        )
        cm.input_parameter.mccs_master_dev_name = self.MCCSMasterNodeFQDN or ""
        cm.update_input_parameter()
        return cm

    def init_command_objects(self):
        super().init_command_objects()
        for (command_name, method_name) in [
            ("TelescopeOn", "telescope_on"),
            ("TelescopeStandby", "telescope_standby"),
        ]:
            self.register_command_object(
                command_name,
                SubmittedSlowCommand(
                    command_name,
                    self._command_tracker,
                    self.component_manager,
                    method_name,
                    logger=None,
                ),
            )


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    """
    Runs the CentralNode.
    :param args: Arguments internal to TANGO

    :param kwargs: Arguments internal to TANGO

    :return: CentralNode TANGO object.
    """
    return run((CentralNodeLow,), args=args, **kwargs)


if __name__ == "__main__":
    main()
