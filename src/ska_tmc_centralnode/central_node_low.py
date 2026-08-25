"""
Central Node is a coordinator of the complete M&C system.
Central Node implements the standard set
of state and mode attributes defined by the SKA Control Model.
"""

from ska_tango_base.software_bus import attribute_from_signal
from ska_tmc_common.op_state_model import TMCOpStateModel
from tango import AttrWriteType
from tango.server import device_property, run

from ska_tmc_centralnode.central_node import AbstractCentralNode
from ska_tmc_centralnode.manager.component_manager_config import (
    ArrayLayoutConfig,
    LowCentralNodeComponentManagerConfig,
    TimeoutConfig,
)
from ska_tmc_centralnode.manager.component_manager_low import (
    CNComponentManagerLow,
)
from ska_tmc_centralnode.model.component import CentralComponent
from ska_tmc_centralnode.model.input import InputParameterLow

__all__ = ["LowTmcCentralNode", "main"]


# pylint:disable=invalid-name #Due to tango camel case
class LowTmcCentralNode(AbstractCentralNode):
    """
    Central Node is a coordinator of the complete Telescope system
    """

    InitCommand = None

    # -----------------
    # Device Properties
    # -----------------
    MCCSMasterLeafNodeFQDN = device_property(dtype="str", default_value="")

    MCCSMasterFQDN = device_property(dtype="str", default_value="")

    IsAutoRecoveryEnabled = device_property(
        dtype=bool,
        default_value=False,
    )

    # ----------
    # Attributes
    # ----------

    # ---------------
    # General methods
    # ---------------

    # ------------------
    # Attributes methods
    # ------------------

    assignResourcesSchemaVersion = attribute_from_signal(
        "_component_manager._assign_resources_schema_version",
        dtype=str,
        description="Schema version used for AssignResources.",
        access=AttrWriteType.READ_WRITE,
        write_to_signal=True,
    )

    releaseResourcesSchemaVersion = attribute_from_signal(
        "_component_manager._release_resources_schema_version",
        dtype=str,
        description="Schema version used for ReleaseResources.",
        access=AttrWriteType.READ_WRITE,
        write_to_signal=True,
    )

    def _get_component_manager_config(
        self,
    ) -> LowCentralNodeComponentManagerConfig:
        """Provides the configuration for component manager Low.

        :return: Instance of LowCentralNodeComponentManagerConfig.
        :rtype: LowCentralNodeComponentManagerConfig
        """
        _component = CentralComponent(logger=self.logger)
        _component.shared_bus = self.shared_bus
        self.op_state_model = TMCOpStateModel(
            logger=self.logger, callback=super()._update_state
        )

        default_array_layout_url_dict = {
            "source_uris": [self.DefaultArrayLayoutSourceURIs],
            "array_layout_path": self.DefaultArrayLayoutPath,
        }
        return LowCentralNodeComponentManagerConfig(
            component=_component,
            op_state_model=self.op_state_model,
            input_parameter=InputParameterLow(None),
            logger=self.logger,
            timeout_config=TimeoutConfig(
                command_timeout=self.CommandTimeOutDefault,
                proxy_timeout=self.ProxyTimeout,
                event_subscription_check_period=(
                    self.EventSubscriptionCheckPeriod
                ),
                liveliness_check_period=self.LivelinessCheckPeriod,
            ),
            array_layout_config=ArrayLayoutConfig(
                default_url=default_array_layout_url_dict,
            ),
            subarray_trl_prefix=self.SubarrayPrefix,
            is_auto_recovery_enabled=self.IsAutoRecoveryEnabled,
        )

    def _update_fqdns(self, cm: CNComponentManagerLow) -> None:
        """Updates the FQDN's in input parameter.

        :param cm: Instance of CNComponentManagerLow.
        :type cm: CNComponentManagerLow
        """
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

    # pylint:enable=invalid-name

    def create_component_manager(self):
        cm = CNComponentManagerLow(config=self._get_component_manager_config())
        self._update_fqdns(cm)
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
