"""
Central Node is a coordinator of the complete M&C system.
Central Node implements the standard set
of state and mode attributes defined by the SKA Control Model.
"""

from ska_tango_base.commands import ResultCode
from ska_tmc_common.op_state_model import TMCOpStateModel
from tango.server import device_property, run

from ska_tmc_centralnode.central_node import AbstractCentralNode
from ska_tmc_centralnode.manager.component_manager_low import (
    CNComponentManagerLow,
)
from ska_tmc_centralnode.model.input import InputParameterLow

__all__ = ["LowTmcCentralNode", "main"]

# pylint:disable = attribute-defined-outside-init


class LowTmcCentralNode(AbstractCentralNode):
    """
    Central Node is a coordinator of the complete Telescope system
    """

    # -----------------
    # Device Properties
    # -----------------
    MCCSMasterLeafNodeFQDN = device_property(dtype="str")

    MCCSMasterFQDN = device_property(dtype="str")

    # ----------
    # Attributes
    # ----------

    # def communication_state_callback(self):
    #     """communication state callabacks"""

    # def component_state_callback(self):
    #     """component state callbacks"""

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

            :return: A tuple containing a return code and a string message
                indicating status.The message is for information purpose only.

            :rtype: (ReturnCode, str)
            """
            super().do()

            return (ResultCode.OK, "")

    # ------------------
    # Attributes methods
    # ------------------

    def create_component_manager(self):
        self.op_state_model = TMCOpStateModel(
            logger=self.logger, callback=super()._update_state
        )
        cm = CNComponentManagerLow(
            self.op_state_model,
            logger=self.logger,
            _update_device_callback=self.update_device_callback,
            _update_telescope_state_callback=(
                self.update_telescope_state_callback
            ),
            _update_telescope_health_state_callback=(
                self.update_telescope_health_state_callback
            ),
            _update_tmc_op_state_callback=self.update_tmc_op_state_callback,
            _update_imaging_callback=None,
            _telescope_availability_callback=(
                self.update_telescope_availability_callback
            ),
            command_timeout=self.CommandTimeOut,
            assignresources_interface=self.AssignResourcesInterface,
            releaseresources_interface=self.ReleaseResourcesInterface,
            proxy_timeout=self.ProxyTimeout,
            _input_parameter=InputParameterLow(None),
            event_subscription_check_period=self.EventSubscriptionCheckPeriod,
            liveliness_check_period=self.LivelinessCheckPeriod,
            skuid_service=self.SkuidService,
            subarray_trl_prefix_trl=self.SubarrayPrefix,
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
        cm.input_parameter.csp_subarray_dev_names = self.CspSubarrayLeafNodes
        cm.input_parameter.sdp_subarray_dev_names = self.SdpSubarrayLeafNodes
        cm.update_input_parameter()
        cm.setup_event_subscription()
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
    return run((LowTmcCentralNode,), args=args, **kwargs)


if __name__ == "__main__":
    main()
