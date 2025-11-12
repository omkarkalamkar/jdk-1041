"""
Central Node is a coordinator of the complete M&C system.
Central Node implements the standard set
of state and mode attributes defined by the SKA Control Model.
"""

# pylint:disable = attribute-defined-outside-init
import json

from ska_tango_base.commands import ResultCode, SubmittedSlowCommand
from ska_tmc_common.op_state_model import TMCOpStateModel
from tango import AttrWriteType, DebugIt
from tango.server import attribute, command, device_property, run

from ska_tmc_centralnode.central_node import AbstractCentralNode
from ska_tmc_centralnode.manager.component_manager_mid import (
    CNComponentManagerMid,
)
from ska_tmc_centralnode.model.enum import DishConfigStatus, ModesAvailability
from ska_tmc_centralnode.model.input import InputParameterMid

__all__ = ["MidTmcCentralNode", "main"]


class MidTmcCentralNode(AbstractCentralNode):
    """
    Central Node is a coordinator of the complete Telescope system

    """

    # -----------------
    # Device Properties
    # -----------------

    DishIDs = device_property(
        dtype=("str",),
        doc="List of the available dish ids",
        default_value=tuple(),
    )

    DishLeafNodePrefix = device_property(
        dtype="str",
        default_value="",
        doc="Device name prefix for Dish Leaf Node",
    )

    DishMasterFQDNs = device_property(
        dtype=("str",),
        doc="List of Dish Master devices",
        default_value=tuple(),
    )

    DishMasterIdentifier = device_property(
        dtype="str",
        doc="Device name tag for Dish Master device",
        default_value="",
    )

    DishVccUri = device_property(
        dtype="str",
        doc="Default DishVccConfig URI",
        default_value="",
    )

    DishVccFilePath = device_property(
        dtype="str",
        doc="Default DishVccConfig File Path",
        default_value="",
    )

    EnableDishVccInit = device_property(
        dtype=bool,
        doc="If true then only load dish vcc during initialization",
        default_value=True,
    )

    DishVccInitTimeout = device_property(dtype="DevUShort", default_value=120)

    DishKvalueAggregationAllowedPercent = device_property(
        dtype="DevDouble", default_value=100.0
    )

    KValueValidRangeUpperLimit = device_property(
        dtype=int,
        default_value=1177,
        doc="the valid k-value range",
    )

    KValueValidRangelowerLimit = device_property(
        dtype=int,
        default_value=1,
        doc="the valid k-value range",
    )

    GPMVersion = device_property(dtype="str", default_value="")

    GPMInterface = device_property(
        dtype="str",
        doc="Default GPM interface",
        default_value="",
    )

    GPMDataSourcesPrefix = device_property(
        dtype="str",
        doc="Default GPM data source prefix",
        default_value="",
    )

    GPMFilePathPrefix = device_property(
        dtype="str",
        doc="Default GPM data file path prefix",
        default_value="",
    )

    DefaultArrayLayoutSourceURIs = device_property(
        dtype=("str",),
        doc=(
            "Default source URIs for the Array Layout. "
            "Defines the TelModel repository source(s). Example: "
            '["gitlab://gitlab.com/ska-telescope/'
            'ska-telmodel-data?main#tmdata"]'
        ),
        default_value=[
            "gitlab://gitlab.com/ska-telescope/ska-telmodel-data?main#tmdata"
        ],
    )

    DefaultArrayLayoutPath = device_property(
        dtype="str",
        doc=(
            "Default array layout path within the TelModel data. "
            "Example: 'instrument/ska1_mid/layout/mid-layout.json'"
        ),
        # default_value="",
        default_value="instrument/ska1_mid/layout/mid-layout.json",
    )

    # ----------
    # Attributes
    # ----------

    imaging = attribute(
        dtype=ModesAvailability,
        access=AttrWriteType.READ,
        doc="Imaging Attribute",
    )

    pss = attribute(
        dtype=ModesAvailability, access=AttrWriteType.READ, doc="PSS Attribute"
    )

    pst = attribute(
        dtype=ModesAvailability, access=AttrWriteType.READ, doc="PST Attribute"
    )

    vlbi = attribute(
        dtype=ModesAvailability,
        access=AttrWriteType.READ,
        doc="VLBI Attribute",
    )

    isDishVccConfigSet = attribute(
        dtype=bool,
        access=AttrWriteType.READ,
    )

    DishVccCommandStatus = attribute(
        dtype=DishConfigStatus,
        access=AttrWriteType.READ,
    )

    DishVccValidationStatus = attribute(
        dtype=str,
        access=AttrWriteType.READ,
    )

    GlobalPointingModelStatus = attribute(
        dtype=str,
        access=AttrWriteType.READ,
    )

    def update_imaging_callback(self, imaging):
        """Callback for Update imaging"""
        self.logger.debug("Imaging %s", imaging)
        self.push_change_archive_events("imaging", imaging)

    def update_dishvccconfig_callback(self, isdishvccconfigset):
        """Update isDishVccConfigSet callbacks"""
        try:
            self.push_change_archive_events(
                "isDishVccConfigSet", isdishvccconfigset
            )

        except Exception as exception:
            self.logger.exception(
                "Exception while pushing event for isDishVccConfigSet: %s",
                exception,
            )

    def dishvcccommandstatus_cb(
        self, dish_vcc_command_status: DishConfigStatus
    ) -> None:
        """
        Update dish_vcc_command_status callbacks

        Args:
            dish_vcc_command_status (DishConfigStatus):
                Dish VCC command status

        """
        try:
            self.push_change_archive_events(
                "DishVccCommandStatus", dish_vcc_command_status
            )

        except Exception as exception:
            self.logger.exception(
                "Exception while pushing event for "
                "Dish Vcc command status: %s",
                exception,
            )

    def dishvccvalidation_callback(self, dishvccvalidationstatus) -> None:
        """
        Update DishVccValidationStatus callbacks

        Args:
            dishvccvalidationstatus: Dish VCC Validation status

        """
        try:
            self.push_change_archive_events(
                "DishVccValidationStatus", dishvccvalidationstatus
            )
        except Exception as exception:
            self.logger.exception(
                "Exception while pushing event for "
                "Dish Vcc Validation Status: %s",
                exception,
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

            :return: A tuple containing a return code and a string message
                indicating status.The message is for information purpose only.

            :rtype: (ReturnCode, str)
            """
            super().do()
            for attribute_name in [
                "imaging",
                "isDishVccConfigSet",
                "DishVccValidationStatus",
                "DishVccCommandStatus",
                "GlobalPointingModelStatus",
            ]:
                self._device.set_change_event(attribute_name, True, False)
                self._device.set_archive_event(attribute_name, True)
            return (ResultCode.OK, "")

    # ------------------
    # Attributes methods
    # ------------------

    def read_imaging(self):
        """Read Attribute for imaging"""
        return self.component_manager.component.imaging

    def read_pss(self):
        """Read attribute for pss"""
        return self.component_manager.component.pss

    def read_pst(self):
        """Read attribute value of pst"""
        return self.component_manager.component.pst

    def read_vlbi(self):
        """Read attribute value of vlbi"""
        return self.component_manager.component.vlbi

    def read_isDishVccConfigSet(self):
        """Return the isDishVccConfigSet attribute."""
        return self.component_manager.is_dish_vcc_config_set

    def read_DishVccValidationStatus(self):
        """Return the DishVccValidationStatus"""
        return self.component_manager.dish_vcc_validation_status

    def read_DishVccCommandStatus(self):
        """Return the DishVccCommandStatus attribute."""
        return self.component_manager.dish_vcc_command_status

    def read_GlobalPointingModelStatus(self):
        """Return the DishVccCommandStatus attribute."""
        return json.dumps(self.component_manager.global_pointing_model_status)

    def create_component_manager(self):
        self.op_state_model = TMCOpStateModel(
            logger=self.logger, callback=super()._update_state
        )
        cm = CNComponentManagerMid(
            self.op_state_model,
            _input_parameter=InputParameterMid(None),
            logger=self.logger,
            _dish_vcc_command_status_callback=self.dishvcccommandstatus_cb,
            _update_device_callback=self.update_device_callback,
            _update_telescope_state_callback=(
                self.update_telescope_state_callback
            ),
            _update_telescope_health_state_callback=(
                self.update_telescope_health_state_callback
            ),
            _update_tmc_op_state_callback=self.update_tmc_op_state_callback,
            _update_imaging_callback=self.update_imaging_callback,
            _telescope_availability_callback=(
                self.update_telescope_availability_callback
            ),
            _update_dishvccconfig_callback=self.update_dishvccconfig_callback,
            _dishvccvalidation_callback=self.dishvccvalidation_callback,
            command_timeout=self.CommandTimeOutDefault,
            proxy_timeout=self.ProxyTimeout,
            event_subscription_check_period=self.EventSubscriptionCheckPeriod,
            liveliness_check_period=self.LivelinessCheckPeriod,
            dish_vcc_uri=self.DishVccUri if self.DishVccUri else "",
            dish_vcc_file_path=(
                self.DishVccFilePath if self.DishVccFilePath else ""
            ),
            dish_vcc_init_timeout=self.DishVccInitTimeout,
            dishKvalueAggregationAllowedPercent=(
                self.DishKvalueAggregationAllowedPercent
            ),
            k_value_valid_range_upper_limit=self.KValueValidRangeUpperLimit,
            k_value_valid_range_lower_limit=self.KValueValidRangelowerLimit,
            invoke_load_dish_cfg_command_callback=(
                self.invoke_load_dish_cfg_command_callback
            ),
            invoke_set_gpm_command_callback=(
                self.invoke_set_gpm_command_callback
            ),
            enable_dish_vcc_init=self.EnableDishVccInit,
            subarray_trl_prefix=self.SubarrayPrefix,
            gpm_version=self.GPMVersion,
            gpm_interface=self.GPMInterface,
            gpm_data_sources_prefix=self.GPMDataSourcesPrefix,
            gpm_file_path_prefix=self.GPMFilePathPrefix,
            default_array_layout_source_uris=self.DefaultArrayLayoutSourceURIs,
            default_array_layout_path=self.DefaultArrayLayoutPath,
            array_layout_url_callback=self.update_array_layout_url_callback,
            default_array_layout_url_callback=(
                self.update_default_array_layout_url_callback
            ),
        )

        cm.input_parameter.dish_leaf_node_dev_names = []
        cm.input_parameter.dish_dev_names = []
        for dish in self.DishIDs:
            if "MKT" in dish:
                continue

            # For now get FQDNs for SKA dishes only
            dish_id = dish[3:]
            cm.input_parameter.dish_leaf_node_dev_names.append(
                self.DishLeafNodePrefix + dish_id
            )

        for dish_name in self.DishMasterFQDNs:
            if ("ska" in dish_name) or ("SKA" in dish_name):
                cm.input_parameter.dish_dev_names.append(dish_name)

        cm.input_parameter.subarray_dev_names = self.TMCSubarrayNodes
        cm.input_parameter.csp_master_dev_name = self.CspMasterFQDN or ""
        cm.input_parameter.csp_mln_dev_name = self.CspMasterLeafNodeFQDN or ""
        cm.input_parameter.sdp_master_dev_name = self.SdpMasterFQDN or ""
        cm.input_parameter.sdp_mln_dev_name = self.SdpMasterLeafNodeFQDN or ""
        cm.input_parameter.csp_subarray_dev_names = self.CspSubarrayLeafNodes
        cm.input_parameter.sdp_subarray_dev_names = self.SdpSubarrayLeafNodes
        cm.input_parameter.dish_leaf_node_prefix = self.DishLeafNodePrefix
        cm.input_parameter.dish_master_identifier = self.DishMasterIdentifier

        cm.update_input_parameter()
        cm.setup_event_subscription()
        return cm

    def init_command_objects(self):
        """
        Initialises the command handlers for commands supported by this device.
        """
        super().init_command_objects()
        # LoadDishCfg command is specific to Mid so register it in Mid only
        for command_name, method_name in [
            ("LoadDishCfg", "load_dish_cfg"),
            ("SetGlobalPointingModel", "set_gpm_version"),
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

    def invoke_load_dish_cfg_command_callback(self):
        """This callback is called when dishVccValidationResult is Unknown
        and Central Node needs to load dish cfg on csp
        """
        handler = self.get_command_object("LoadDishCfg")
        dish_cfg_json = json.dumps(
            self.component_manager.get_default_dish_vcc_config_params()
        )
        handler(dish_cfg_json)

    def invoke_set_gpm_command_callback(self):
        """This callback is called when dishVccValidationResult is Unknown
        and Central Node needs to load dish cfg on csp
        """

        handler = self.get_command_object("SetGlobalPointingModel")
        handler(
            json.dumps(self.component_manager.get_default_gpm_version_params())
        )

    def is_LoadDishCfg_allowed(self):
        """
        Checks whether LoadDishCfg command is allowed to be run
        in current device state.

        :rtype: boolean
        """
        return True

    @command(
        dtype_in="str",
        doc_in="The string in JSON format.",
        dtype_out="DevVarLongStringArray",
        doc_out="information-only string",
    )
    @DebugIt()
    def LoadDishCfg(self, argin):
        """
        LoadDishCfg command to load dishID-vcc map config.
        This command get dishid-vcc map json string from Telmodel
        based on tm data sources provided in argin.

        .. code-block::
            :caption: Example

            {
                "interface":
                "https://schema.skao.int/ska-mid-cbf-initial-parameters/2.2",
                "tm_data_sources":["car://gitlab.com/ska-telescope/
                ska-tmc/ska-tmc-simulators?main#tmdata"],
                "tm_data_filepath": "instrument/dishid_vcc_map_configuration/
                mid_cbf_initial_parameters.json"
            }

        """
        handler = self.get_command_object("LoadDishCfg")
        result_code, unique_id = handler(argin)
        return [[result_code], [str(unique_id)]]

    def is_setGlobalPointingModel_allowed(self):
        """
        Checks whether setGlobalPointingModel command is allowed to be run
        in current device state.

        :rtype: boolean
        """
        return True

    @command(
        dtype_in="str",
        doc_in="The string in JSON format.",
        dtype_out="DevVarLongStringArray",
        doc_out="information-only string",
    )
    @DebugIt()
    def SetGlobalPointingModel(self, argin):
        """
        SetGlobalPointingModel command to send the GPM URI to dish leaf
        nodes. This command gets a dictionary in following form:

        .. code-block::
            :caption: Example

            {
                # Versioned tag of git where all the GPM files are available
                # for applying to the respective dishes for their respective
                # bands.
                "version": "1.0",
                "receptors":
                    {
                        "SKA001":['Band_1','Band_2'],
                        "SKA002":['Band_2']
                    }
            }
            Data formed for Dish Leaf node ApplyPointingModel command:
            {
                "interface": "https://schema.skao.int/ska-mid-global
                -pointing-model/1.0",
                "tm_data_sources":
                ["car://gitlab.com/ska-telescope/ska-tmc/ska-tmc-simu
                lators?1.0#tmdata"],
                "tm_data_filepath":
                "instrument/ska_mid1/global_pointing_model_data/gpm-
                ska001-Band_1.json"
            }
        """
        handler = self.get_command_object("SetGlobalPointingModel")
        result_code, unique_id = handler(argin)
        return [[result_code], [str(unique_id)]]


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
    return run((MidTmcCentralNode,), args=args, **kwargs)


if __name__ == "__main__":
    main()
