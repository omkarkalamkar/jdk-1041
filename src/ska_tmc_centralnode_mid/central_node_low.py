"""
Central Node is a coordinator of the complete M&C system.
Central Node implements the standard set
of state and mode attributes defined by the SKA Control Model.
"""
from ska_ser_skuid.client import SkuidClient
from ska_tango_base.commands import ResultCode
from tango import AttrWriteType
from tango.server import attribute, device_property, run

from ska_tmc_centralnode_mid.central_node import AbstractCentralNode
from ska_tmc_centralnode_mid.commands.assign_resources_command import (
    AssignResources,
)
from ska_tmc_centralnode_mid.commands.release_resources_command import (
    ReleaseResources,
)
from ska_tmc_centralnode_mid.commands.telescope_off_command import TelescopeOff
from ska_tmc_centralnode_mid.commands.telescope_on_command import TelescopeOn
from ska_tmc_centralnode_mid.commands.telescope_standby_command import (
    TelescopeStandby,
)
from ska_tmc_centralnode_mid.manager.component_manager import (
    CNComponentManager,
)
from ska_tmc_centralnode_mid.model.input import InputParameterLow
from ska_tmc_centralnode_mid.model.op_state_model import TMCOpStateModel

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
        """Return the MccsMasterLeafNodeName attribute."""
        return self.component_manager.input_parameter.mccs_master_leaf_node

    def write_mccsMasterLeafNodeName(self, value):
        """Set the MccsMasterLeafNodeName attribute."""
        self.component_manager.input_parameter.mccs_master_leaf_node = value
        self.component_manager.update_input_parameter()

    def read_mccsSubarrayLeafNodeName(self):
        """Return the MccsSubarrayLeafNodeName attribute."""
        return self.component_manager.input_parameter.mccs_subarray_leaf_node

    def write_mccsSubarrayLeafNodeName(self, value):
        """Set the MccsSubarrayNodeDevName attribute."""
        self.component_manager.input_parameter.mccs_subarray_leaf_node = value
        self.component_manager.update_input_parameter()

    def read_mccsMasterNodeName(self):
        """Return the CspMasterDevName attribute."""
        return self.component_manager.input_parameter.mccs_master_dev_name

    def write_mccsMasterNodeName(self, value):
        """Set the CspMasterDevName attribute."""
        self.component_manager.input_parameter.mccs_master_dev_name = value
        self.component_manager.update_input_parameter()

    def init_command_objects(self):
        """
        Initialises the command handlers for commands supported by this device.
        """
        super().init_command_objects()
        args = ()
        for (command_name, command_class) in [
            ("On", TelescopeOn),
            ("TelescopeOn", TelescopeOn),
            ("Off", TelescopeOff),
            ("TelescopeOff", TelescopeOff),
            ("StartUpTelescope", TelescopeOn),
            ("StandByTelescope", TelescopeOff),
            ("ReleaseResources", ReleaseResources),
            ("Standby", TelescopeStandby),
            ("TelescopeStandby", TelescopeStandby),
        ]:
            command_obj = command_class(
                self.component_manager,
                self.op_state_model,
                *args,
                logger=self.logger,
            )
            self.register_command_object(command_name, command_obj)
        assign_resources_obj = AssignResources(
            self.component_manager,
            self.op_state_model,
            skuid=SkuidClient(skuid_url=self.SkuidServiceNamePort),
            *args,
            logger=self.logger,
        )
        self.register_command_object("AssignResources", assign_resources_obj)

    def create_component_manager(self):
        # if the init is called more than once
        # I need to stop all threads
        if hasattr(self, "component_manager"):
            self.component_manager.stop()

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
            _update_subarray_health_state_callback=self.update_subarray_health_state_callback,
            _update_imaging_callback=None,
            _update_command_in_progress_callback=self.update_command_in_progress_callback,
            max_workers=self.MaxWorkerMonitoringLoop,
            proxy_timeout=self.ProxyTimeoutMonitoringLoop,
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
