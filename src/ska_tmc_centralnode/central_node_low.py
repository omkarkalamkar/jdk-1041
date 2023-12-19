"""
Central Node is a coordinator of the complete M&C system.
Central Node implements the standard set
of state and mode attributes defined by the SKA Control Model.
"""
from ska_tango_base.commands import ResultCode
from ska_tmc_common.op_state_model import TMCOpStateModel
from tango import AttrWriteType
from tango.server import attribute, device_property, run

from ska_tmc_centralnode.central_node import AbstractCentralNode
from ska_tmc_centralnode.manager.component_manager_low import (
    CNComponentManagerLow,
)
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

    MCCSMasterFQDN = device_property(dtype="str")

    CspMasterLeafNodeFQDN = device_property(dtype="str")

    CspMasterFQDN = device_property(dtype="str")

    SdpMasterLeafNodeFQDN = device_property(dtype="str")

    SdpMasterFQDN = device_property(dtype="str")

    TMCLowCspSubarrayLeafNodes = device_property(
        dtype=("str",),
        doc="List of Low CspSubarrayLeafNode devices",
        default_value=tuple(),
    )

    TMCLowSdpSubarrayLeafNodes = device_property(
        dtype=("str",),
        doc="List of Low SdpSubarrayLeafNode devices",
        default_value=tuple(),
    )

    # ----------
    # Attributes
    # ----------

    cspMasterDevName = attribute(
        dtype="DevString",
        access=AttrWriteType.READ_WRITE,
    )

    sdpMasterDevName = attribute(
        dtype="DevString",
        access=AttrWriteType.READ_WRITE,
    )

    CspMasterLeafNodeDevName = attribute(
        dtype="DevString",
        access=AttrWriteType.READ_WRITE,
    )

    SdpMasterLeafNodeDevName = attribute(
        dtype="DevString",
        access=AttrWriteType.READ_WRITE,
    )

    mccsMasterLeafNodeName = attribute(
        dtype="DevString",
        access=AttrWriteType.READ_WRITE,
    )
    mccsMasterName = attribute(
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
        """Return the mccsMasterLeafNodeName attribute."""
        return self.component_manager.input_parameter.mccs_mln_dev_name

    def write_mccsMasterLeafNodeName(self, value):
        """Set the mccsMasterLeafNodeName attribute."""
        self.component_manager.input_parameter.mccs_mln_dev_name = value
        self.component_manager.update_input_parameter()

    def read_mccsMasterName(self):
        """Return the mccsMasterName attribute."""
        return self.component_manager.input_parameter.mccs_master_dev_name

    def write_mccsMasterName(self, value):
        """Set the mccsMasterName attribute."""
        self.component_manager.input_parameter.mccs_master_dev_name = value
        self.component_manager.update_input_parameter()

    def read_cspMasterDevName(self):
        """Return the cspMasterDevName attribute."""
        return self.component_manager.input_parameter.csp_master_dev_name

    def write_cspMasterDevName(self, value):
        """Set the cspMasterDevName attribute."""
        self.component_manager.input_parameter.csp_master_dev_name = value
        self.component_manager.update_input_parameter()

    def read_sdpMasterDevName(self):
        """Return the sdpMasterDevName attribute."""
        return self.component_manager.input_parameter.sdp_master_dev_name

    def write_sdpMasterDevName(self, value):
        """Set the sdpMasterDevName attribute."""
        self.component_manager.input_parameter.sdp_master_dev_name = value
        self.component_manager.update_input_parameter()

    def read_CspMasterLeafNodeDevName(self):
        """Return the cspMasterLeafNodeDevName attribute."""
        return self.component_manager.input_parameter.csp_mln_dev_name

    def write_CspMasterLeafNodeDevName(self, value):
        """Set the cspMasterLeafNodeDevName attribute."""
        self.component_manager.input_parameter.csp_mln_dev_name = value
        self.component_manager.update_input_parameter()

    def read_SdpMasterLeafNodeDevName(self):
        """Return the sdpMasterLeafNodeDevName attribute."""
        return self.component_manager.input_parameter.sdp_mln_dev_name

    def write_SdpMasterLeafNodeDevName(self, value):
        """Set the sdpMasterLeafNodeDevName attribute."""
        self.component_manager.input_parameter.sdp_mln_dev_name = value
        self.component_manager.update_input_parameter()

    def create_component_manager(self):
        self.op_state_model = TMCOpStateModel(
            logger=self.logger, callback=super()._update_state
        )
        cm = CNComponentManagerLow(
            self.op_state_model,
            logger=self.logger,
            _update_device_callback=self.update_device_callback,
            _update_telescope_state_callback=self.update_telescope_state_callback,
            _update_telescope_health_state_callback=self.update_telescope_health_state_callback,
            _update_tmc_op_state_callback=self.update_tmc_op_state_callback,
            _update_imaging_callback=None,
            _telescope_availability_callback=self.update_telescope_availability_callback,
            communication_state_callback=None,
            component_state_callback=None,
            command_timeout=self.CommandTimeout,
            max_workers=self.MaxWorker,
            proxy_timeout=self.ProxyTimeout,
            _input_parameter=InputParameterLow(None),
            sleep_time=self.SleepTime,
        )
        cm.input_parameter.subarray_dev_names = self.TMCSubarrayNodes
        cm.input_parameter.mccs_mln_dev_name = (
            self.MCCSMasterLeafNodeFQDN or ""
        )
        cm.input_parameter.mccs_master_dev_name = self.MCCSMasterFQDN or ""
        cm.input_parameter.sdp_master_dev_name = self.SdpMasterFQDN or ""
        cm.input_parameter.sdp_mln_dev_name = self.SdpMasterLeafNodeFQDN or ""
        cm.input_parameter.csp_master_dev_name = self.CspMasterFQDN or ""
        cm.input_parameter.csp_mln_dev_name = self.CspMasterLeafNodeFQDN or ""
        cm.input_parameter.csp_subarray_dev_names = (
            self.TMCLowCspSubarrayLeafNodes
        )
        cm.input_parameter.sdp_subarray_dev_names = (
            self.TMCLowSdpSubarrayLeafNodes
        )
        cm.update_input_parameter()
        return cm

    def init_command_objects(self):
        """
        Initialises the command handlers for commands supported by this device.
        """
        super().init_command_objects()


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
