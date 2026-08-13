"""
Central Node is a coordinator of the complete M&C system.
Central Node implements the standard set
of state and mode attributes defined by the SKA Control Model.
"""

# pylint:disable = attribute-defined-outside-init
import json
from threading import Event
from typing import Union

import tango
from ska_control_model import HealthState
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.long_running_commands import (
    LRCReqType,
    long_running_command,
)
from ska_tango_base.software_bus import (
    Signal,
    attribute_from_signal,
    listen_to_signal,
)
from ska_tango_base.type_hints import TaskFunctionType
from ska_tmc_common.exceptions import CommandNotAllowed, DeviceUnresponsive
from ska_tmc_common.v1.tmc_base_device import TMCBaseDevice
from tango import ApiUtil, AttrWriteType, Database, DebugIt
from tango.server import command, device_property

from ska_tmc_centralnode import release
from ska_tmc_centralnode.utils.json_validator_decorator import (
    assign_validate_json_args,
    release_validate_json_args,
)


class AbstractCentralNode(TMCBaseDevice):
    """
    Central Node is a coordinator of the complete Telescope system.
    Central Node is inherited from TMCBaseDevice class which is further
    inherited from SKABaseDevice class. TMCBaseDevice class contains
    attributes common to CentralNode and SubarrayNode.
    """

    InitCommand = None

    # -----------------
    # Device Properties
    # -----------------
    def _memorize_attr(self, attr_name: str, json_string_value: str) -> None:
        """
        Persist an attribute value into Tango DB in the right format.
        attr_name must match the Tango attribute name exactly.
        json_string_value must be a JSON-encoded string (ex:json.dumps(dict)).
        """
        try:
            db = Database()
            props = {attr_name: {"__value": [json_string_value]}}
            # Use the server's own FQDN
            device_fqdn = self.get_name()
            db.put_device_attribute_property(device_fqdn, props)
            self.logger.debug(
                "Memorized %s in DB with value: %s",
                attr_name,
                json_string_value,
            )
        except Exception:
            # Don't crash your server if DB is unavailable
            self.logger.exception("Failed to memorize %s in DB", attr_name)

    @listen_to_signal("_component_manager._array_layout_url")
    def update_array_layout_url_callback(self, url_dict: dict) -> None:
        """
        Called by the component manager whenever the array_layout_url changes.
        Persists the value in the Tango DB and pushes change/archive events.

        Args:
            url_dict (dict): Dictionary containing the array layout URL
            information to be serialized and stored.
        """
        json_value = json.dumps(url_dict)
        self._memorize_attr("arrayLayoutURL", json_value)
        self._array_layout_url = json_value

    @listen_to_signal("_component_manager._default_array_layout_url")
    def update_default_array_layout_url_callback(self, url_dict: dict) -> None:
        """
        Called by the component manager whenever the default_array_layout_url
        changes. Persists the value in the Tango DB and pushes change/archive
        events.

        Args:
            url_dict (dict): Dictionary containing the default array layout URL
                information to be serialized and stored.
        """
        json_value = json.dumps(url_dict)
        self._memorize_attr("DefaultArrayLayoutURL", json_value)
        self._default_array_layout_url = json_value
        if not url_dict:
            self._array_layout_file_provided = False
        elif (
            url_dict["array_layout_path"] == ""
            or url_dict["array_layout_path"] is None
        ):
            self._array_layout_file_provided = False
        elif (
            url_dict["source_uris"] == [""] or url_dict["source_uris"] is None
        ):
            self._array_layout_file_provided = False
        else:
            self._array_layout_file_provided = True
        self.logger.info("DefaultArrayLayoutURL is set to %s", url_dict)
        self.logger.info(
            "arrayLayoutFileProvided is set to %s",
            self._array_layout_file_provided,
        )

    TMCSubarrayNodes = device_property(
        dtype=("str",),
        doc="List of TMC Mid Subarray Node devices",
        default_value=tuple(),
    )
    CspMasterLeafNodeFQDN = device_property(dtype="str", default_value="")

    CspMasterFQDN = device_property(dtype="str", default_value="")

    SdpMasterLeafNodeFQDN = device_property(dtype="str", default_value="")

    SdpMasterFQDN = device_property(dtype="str", default_value="")

    CspSubarrayLeafNodes = device_property(
        dtype=("str",),
        doc="List of CspSubarrayLeafNode devices",
        default_value=tuple(),
    )

    SdpSubarrayLeafNodes = device_property(
        dtype=("str",),
        doc="List of SdpSubarrayLeafNode devices",
        default_value=tuple(),
    )

    ProxyTimeout = device_property(dtype="DevUShort", default_value=500)

    SubarrayPrefix = device_property(
        dtype="DevString",
        default_value="",
    )

    DefaultArrayLayoutSourceURIs = device_property(
        dtype="DevString",
        doc=(
            "Default source URIs for the Array Layout. "
            "Defines the TelModel repository source(s). Example: "
            '["gitlab://gitlab.com/ska-telescope/'
            'ska-telmodel-data?main#tmdata"]'
        ),
    )

    DefaultArrayLayoutPath = device_property(
        dtype="str",
        doc=(
            "Default array layout path within the TelModel data. "
            "Example: 'instrument/ska1_mid/layout/mid-layout.json'"
        ),
    )
    # ----------------------
    # Attributes and methods
    # ----------------------
    _array_layout_file_provided: Signal[bool] = Signal[bool](stored=True)
    arrayLayoutFileProvided = attribute_from_signal(
        _array_layout_file_provided,
        dtype=bool,
        description="Flag to indicate whether array layout file is defined.",
        access=AttrWriteType.READ,
    )
    telescopeHealthState = attribute_from_signal(
        "_component_manager.component._telescope_health_state",
        dtype=HealthState,
        description="Health state of Telescope",
        access=AttrWriteType.READ,
    )

    telescopeState = attribute_from_signal(
        "_component_manager.component._telescope_state",
        dtype=tango.DevState,
        description="State of Telescope",
        access=AttrWriteType.READ,
    )
    desiredTelescopeState = attribute_from_signal(
        "_component_manager.component._desired_telescope_state",
        dtype=tango.DevState,
        description="desiredTelescopeState attribute of Central Node.",
        access=AttrWriteType.READ,
    )

    arrayLayoutURL = attribute_from_signal(
        "_component_manager._array_layout_url",
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        memorized=True,
        hw_memorized=True,
        to_tango=json.dumps,
        from_tango=json.loads,
    )

    DefaultArrayLayoutURL = attribute_from_signal(
        "_component_manager._default_array_layout_url",
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        memorized=True,
        hw_memorized=True,
        from_tango=json.loads,
        to_tango=json.dumps,
    )

    tmOpState = attribute_from_signal(
        "_component_manager.component._tmc_op_state",
        dtype=tango.DevState,
        access=AttrWriteType.READ,
    )

    telescopeAvailability = attribute_from_signal(
        "_component_manager.component._telescope_availability",
        dtype=str,
        access=AttrWriteType.READ,
        to_tango=json.dumps,
    )
    lastDeviceInfoChanged = attribute_from_signal(
        "_component_manager.component._last_device_info_changed",
        dtype=str,
        access=AttrWriteType.READ,
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self) -> None:
        """
        Initializes the CentralNode device.
        """
        super().init_device()
        self._build_state = (
            f"{release.name},{release.version},{release.description}"
        )

        self._version_id = release.version
        self.last_device_info_changed = ""

        ApiUtil.instance().set_asynch_cb_sub_model(
            tango.cb_sub_model.PUSH_CALLBACK
        )
        self._health_state = HealthState.OK
        if (
            self.DefaultArrayLayoutSourceURIs == ""
            or self.DefaultArrayLayoutPath == ""
            or self.DefaultArrayLayoutSourceURIs is None
            or self.DefaultArrayLayoutPath is None
        ):
            self._array_layout_file_provided = False
            self.logger.info(
                "The Default version of the array layout file is not defined."
            )
        else:
            self._array_layout_file_provided = True
            self.logger.info(
                "The Default version of the array layout file is defined."
            )

        self.init_completed()
        self.op_state_model.perform_action("component_on")

    # ------------------
    # Attributes methods
    # ------------------

    def transformedInternalModel_read(self):
        """Tranformed InternalModelRead"""
        result = json.loads(super().transformedInternalModel_read())
        result[
            "telescope_state"
        ] = self.component_manager.get_telescope_state()
        result["tmc_op_state"] = self.component_manager.get_tmc_op_state()
        result[
            "telescope_health_state"
        ] = self.component_manager.get_telescope_health_state()
        return json.dumps(result)

    # --------
    # Commands
    # --------

    def is_TelescopeOn_allowed(
        self, request_type: LRCReqType = LRCReqType.ENQUEUE_REQ
    ) -> Union[bool, CommandNotAllowed, DeviceUnresponsive]:
        """
        Checks whether this command is allowed to be run in current device
            state.

        :return: True if this command is allowed to be run in current device
            state.

        :rtype: boolean
        """
        validator = self.component_manager.cmd_allowed_validator
        if request_type == LRCReqType.ENQUEUE_REQ:
            return self.component_manager.is_command_allowed("TelescopeOn")
        return validator.is_command_allowed_before_lrc_start(
            command_name="TelescopeOn"
        )

    @long_running_command
    @DebugIt()
    def TelescopeOn(self) -> TaskFunctionType:
        """
        This command invokes TelescopeOn() command on DishLeadNode,
        CspMasterLeafNode,SdpMasterLeafNode.
        """

        def task(
            task_callback: TaskCallbackType, task_abort_event: Event
        ) -> None:
            self.component_manager.telescope_on(
                task_callback=task_callback,
                task_abort_event=task_abort_event,
            )

        return task

    def is_TelescopeStandby_allowed(
        self, request_type: LRCReqType = LRCReqType.ENQUEUE_REQ
    ) -> Union[bool, CommandNotAllowed, DeviceUnresponsive]:
        """
        Checks whether this command is allowed to be run in current device
        state.

        :return: True if this command is allowed to be run in current device
            state.

        :rtype: boolean
        """
        validator = self.component_manager.cmd_allowed_validator

        if request_type == LRCReqType.ENQUEUE_REQ:
            return self.component_manager.is_command_allowed(
                "TelescopeStandby"
            )

        return validator.is_command_allowed_before_lrc_start(
            command_name="TelescopeStandby"
        )

    @long_running_command
    @DebugIt()
    def TelescopeStandby(self) -> TaskFunctionType:
        """
        This command invokes TelescopeStandby() command on CspMasterLeafNode,
        SdpMasterLeafNode and DishLeafNode.

        """

        def task(
            task_callback: TaskCallbackType, task_abort_event: Event
        ) -> None:
            self.component_manager.telescope_standby(
                task_callback=task_callback,
                task_abort_event=task_abort_event,
            )

        return task

    def is_TelescopeOff_allowed(
        self, request_type: LRCReqType = LRCReqType.ENQUEUE_REQ
    ) -> Union[bool, CommandNotAllowed, DeviceUnresponsive]:
        """
        Checks whether this command is allowed to be run in current
        device state.

        :return: True if this command is allowed to be run in current
            device state.

        :rtype: boolean
        """
        validator = self.component_manager.cmd_allowed_validator
        if request_type == LRCReqType.ENQUEUE_REQ:
            return self.component_manager.is_command_allowed("TelescopeOff")
        return validator.is_command_allowed_before_lrc_start(
            command_name="TelescopeOff"
        )

    @long_running_command
    @DebugIt()
    def TelescopeOff(self) -> TaskFunctionType:
        """
        This command invokes SetStandbyLPMode() command on DishLeafNode, Off()
        command on CspMasterLeafNode and SdpMasterLeafNode.

        """

        def task(
            task_callback: TaskCallbackType, task_abort_event: Event
        ) -> None:
            self.component_manager.telescope_off(
                task_callback=task_callback,
                task_abort_event=task_abort_event,
            )

        return task

    def is_On_allowed(self):
        """
        Checks whether this command is allowed to be run in current device
        state.

        :return: True if this command is allowed to be run in current device
            state.

        :rtype: boolean

        """
        return self.component_manager.is_command_allowed("On")

    @command(
        dtype_out="DevVarLongStringArray",
    )
    @DebugIt()
    def On(self):
        """
        This command invokes On command on DishLeadNode, TelescopeOn()
            command on CspMasterLeafNode,SdpMasterLeafNode.
        """
        handler = self.get_command_object("On")
        result_code, unique_id = handler()
        return [[result_code], [str(unique_id)]]

    def is_Off_allowed(self):
        """
        Checks whether this command is allowed to be run in current device
        state.

        :return: True if this command is allowed to be run in current device
            state.

        :rtype: boolean
        """
        return self.component_manager.is_command_allowed("Off")

    @command(
        dtype_out="DevVarLongStringArray",
    )
    @DebugIt()
    def Off(self):
        """
        This command invokes SetStandbyLPMode() command on DishLeafNode,
        TelescopeOff() command on CspMasterLeafNode and SdpMasterLeafNode.
        """
        handler = self.get_command_object("Off")
        result_code, unique_id = handler()
        return [[result_code], [str(unique_id)]]

    def is_Standby_allowed(self):
        """
        Checks whether this command is allowed to be run in current device
        state.

        :return: True if this command is allowed to be run in current device
            state.

        :rtype: boolean
        """
        return self.component_manager.is_command_allowed("Standby")

    @command(
        dtype_out="DevVarLongStringArray",
    )
    @DebugIt()
    def Standby(self):
        """
        This command invokes Standby() command on CspMasterLeafNode,
        SdpMasterLeafNode and DishLeafNode.
        """
        handler = self.get_command_object("Standby")
        result_code, unique_id = handler()
        return [[result_code], [str(unique_id)]]

    def is_AssignResources_allowed(
        self, request_type: LRCReqType = LRCReqType.ENQUEUE_REQ
    ) -> Union[bool, CommandNotAllowed, DeviceUnresponsive]:
        """
        Checks whether AssignResources command is allowed with the given input.

        :param argin: The command input argument
        :param request_type: The type of request (ENQUEUE_REQ or EXECUTE_REQ)
        :return: True if AssignResources is allowed
            to be run in current device state

        :rtype: boolean
        """
        if request_type == LRCReqType.ENQUEUE_REQ:
            return self.component_manager.is_command_allowed("AssignResources")

        return True

    # pylint: disable=unnecessary-pass
    def completed_AssignResources(self) -> None:
        """AssignResources command completed callback."""
        pass

    # pylint: enable=unnecessary-pass
    @assign_validate_json_args
    @long_running_command
    @DebugIt()
    def AssignResources(self, argin: str) -> TaskFunctionType:
        """
        AssignResources command invokes the AssignResources command on
            lower level devices.
        """

        def task(
            task_callback: TaskCallbackType, task_abort_event: Event
        ) -> None:
            self.component_manager.assign_resources(
                argin=argin,
                task_callback=task_callback,
                task_abort_event=task_abort_event,
            )

        return task

    def is_ReleaseResources_allowed(
        self, request_type: LRCReqType = LRCReqType.ENQUEUE_REQ
    ) -> Union[bool, CommandNotAllowed, DeviceUnresponsive]:
        """
        Checks whether ReleaseResources is allowed with the given input.

        :param argin: The command input argument
        :param request_type: The type of request (ENQUEUE_REQ or EXECUTE_REQ)
        :return: True if ReleaseResources command is allowed to be run in
            current device state.

        :rtype: boolean
        """
        if request_type == LRCReqType.ENQUEUE_REQ:
            return self.component_manager.is_command_allowed(
                "ReleaseResources"
            )

        return True

    @release_validate_json_args
    @long_running_command
    @DebugIt()
    def ReleaseResources(self, argin: str) -> TaskFunctionType:
        """
        Releases all the resources assigned to the given Subarray.
        """

        def task(
            task_callback: TaskCallbackType, task_abort_event: Event
        ) -> None:
            self.component_manager.release_resources(
                argin=argin,
                task_callback=task_callback,
                task_abort_event=task_abort_event,
            )

        return task

    def create_component_manager(self):
        """Create component manager object for command invocation."""
