==============================
MidTmcCentralNode Tango Device
==============================

    Central Node is a coordinator of the complete Telescope system

    

Properties
----------
.. index::
	single: CommandTimeOutDefault; MidTmcCentralNode.CommandTimeOutDefault

.. py:attribute:: CommandTimeOutDefault
	:module: MidTmcCentralNode

	:data type: DevFloat
	:default value: 30

.. index::
	single: CspMasterFQDN; MidTmcCentralNode.CspMasterFQDN

.. py:attribute:: CspMasterFQDN
	:module: MidTmcCentralNode

	:data type: DevString

.. index::
	single: CspMasterLeafNodeFQDN; MidTmcCentralNode.CspMasterLeafNodeFQDN

.. py:attribute:: CspMasterLeafNodeFQDN
	:module: MidTmcCentralNode

	:data type: DevString

.. index::
	single: CspSubarrayLeafNodes; MidTmcCentralNode.CspSubarrayLeafNodes

.. py:attribute:: CspSubarrayLeafNodes
	:module: MidTmcCentralNode

	List of CspSubarrayLeafNode devices

	:data type: DevVarStringArray

.. index::
	single: DefaultArrayLayoutPath; MidTmcCentralNode.DefaultArrayLayoutPath

.. py:attribute:: DefaultArrayLayoutPath
	:module: MidTmcCentralNode

	Default array layout path within the TelModel data. Example: 'instrument/ska1_mid/layout/mid-layout.json'

	:data type: DevString

.. index::
	single: DefaultArrayLayoutSourceURIs; MidTmcCentralNode.DefaultArrayLayoutSourceURIs

.. py:attribute:: DefaultArrayLayoutSourceURIs
	:module: MidTmcCentralNode

	Default source URIs for the Array Layout. Defines the TelModel repository source(s). Example: ["gitlab://gitlab.com/ska-telescope/ska-telmodel-data?main#tmdata"]

	:data type: DevString

.. index::
	single: DishIDs; MidTmcCentralNode.DishIDs

.. py:attribute:: DishIDs
	:module: MidTmcCentralNode

	List of the available dish ids

	:data type: DevVarStringArray

.. index::
	single: DishKvalueAggregationAllowedPercent; MidTmcCentralNode.DishKvalueAggregationAllowedPercent

.. py:attribute:: DishKvalueAggregationAllowedPercent
	:module: MidTmcCentralNode

	:data type: DevDouble
	:default value: 100.0

.. index::
	single: DishLeafNodePrefix; MidTmcCentralNode.DishLeafNodePrefix

.. py:attribute:: DishLeafNodePrefix
	:module: MidTmcCentralNode

	Device name prefix for Dish Leaf Node

	:data type: DevString

.. index::
	single: DishMasterFQDNs; MidTmcCentralNode.DishMasterFQDNs

.. py:attribute:: DishMasterFQDNs
	:module: MidTmcCentralNode

	List of Dish Master devices

	:data type: DevVarStringArray

.. index::
	single: DishMasterIdentifier; MidTmcCentralNode.DishMasterIdentifier

.. py:attribute:: DishMasterIdentifier
	:module: MidTmcCentralNode

	Device name tag for Dish Master device

	:data type: DevString

.. index::
	single: DishVccFilePath; MidTmcCentralNode.DishVccFilePath

.. py:attribute:: DishVccFilePath
	:module: MidTmcCentralNode

	Default DishVccConfig File Path

	:data type: DevString

.. index::
	single: DishVccInitTimeout; MidTmcCentralNode.DishVccInitTimeout

.. py:attribute:: DishVccInitTimeout
	:module: MidTmcCentralNode

	:data type: DevUShort
	:default value: 120

.. index::
	single: DishVccUri; MidTmcCentralNode.DishVccUri

.. py:attribute:: DishVccUri
	:module: MidTmcCentralNode

	Default DishVccConfig URI

	:data type: DevString

.. index::
	single: EnableDishVccInit; MidTmcCentralNode.EnableDishVccInit

.. py:attribute:: EnableDishVccInit
	:module: MidTmcCentralNode

	If true then only load dish vcc during initialization

	:data type: DevBoolean
	:default value: True

.. index::
	single: EventSubscriptionCheckPeriod; MidTmcCentralNode.EventSubscriptionCheckPeriod

.. py:attribute:: EventSubscriptionCheckPeriod
	:module: MidTmcCentralNode

	:data type: DevFloat
	:default value: 1

.. index::
	single: GPMDataSourcesPrefix; MidTmcCentralNode.GPMDataSourcesPrefix

.. py:attribute:: GPMDataSourcesPrefix
	:module: MidTmcCentralNode

	Default GPM data source prefix

	:data type: DevString

.. index::
	single: GPMFilePathPrefix; MidTmcCentralNode.GPMFilePathPrefix

.. py:attribute:: GPMFilePathPrefix
	:module: MidTmcCentralNode

	Default GPM data file path prefix

	:data type: DevString

.. index::
	single: GPMInterface; MidTmcCentralNode.GPMInterface

.. py:attribute:: GPMInterface
	:module: MidTmcCentralNode

	Default GPM interface

	:data type: DevString

.. index::
	single: GPMVersion; MidTmcCentralNode.GPMVersion

.. py:attribute:: GPMVersion
	:module: MidTmcCentralNode

	:data type: DevString

.. index::
	single: GroupDefinitions; MidTmcCentralNode.GroupDefinitions

.. py:attribute:: GroupDefinitions
	:module: MidTmcCentralNode

	:data type: DevVarStringArray

.. index::
	single: KValueValidRangeUpperLimit; MidTmcCentralNode.KValueValidRangeUpperLimit

.. py:attribute:: KValueValidRangeUpperLimit
	:module: MidTmcCentralNode

	the valid k-value range

	:data type: DevLong64
	:default value: 1177

.. index::
	single: KValueValidRangelowerLimit; MidTmcCentralNode.KValueValidRangelowerLimit

.. py:attribute:: KValueValidRangelowerLimit
	:module: MidTmcCentralNode

	the valid k-value range

	:data type: DevLong64
	:default value: 1

.. index::
	single: LivelinessCheckPeriod; MidTmcCentralNode.LivelinessCheckPeriod

.. py:attribute:: LivelinessCheckPeriod
	:module: MidTmcCentralNode

	:data type: DevFloat
	:default value: 1

.. index::
	single: LoggingLevelDefault; MidTmcCentralNode.LoggingLevelDefault

.. py:attribute:: LoggingLevelDefault
	:module: MidTmcCentralNode

	:data type: DevUShort
	:default value: 4

.. index::
	single: LoggingTargetsDefault; MidTmcCentralNode.LoggingTargetsDefault

.. py:attribute:: LoggingTargetsDefault
	:module: MidTmcCentralNode

	:data type: DevVarStringArray
	:default value: ['tango::logger']

.. index::
	single: ProxyTimeout; MidTmcCentralNode.ProxyTimeout

.. py:attribute:: ProxyTimeout
	:module: MidTmcCentralNode

	:data type: DevUShort
	:default value: 500

.. index::
	single: SdpMasterFQDN; MidTmcCentralNode.SdpMasterFQDN

.. py:attribute:: SdpMasterFQDN
	:module: MidTmcCentralNode

	:data type: DevString

.. index::
	single: SdpMasterLeafNodeFQDN; MidTmcCentralNode.SdpMasterLeafNodeFQDN

.. py:attribute:: SdpMasterLeafNodeFQDN
	:module: MidTmcCentralNode

	:data type: DevString

.. index::
	single: SdpSubarrayLeafNodes; MidTmcCentralNode.SdpSubarrayLeafNodes

.. py:attribute:: SdpSubarrayLeafNodes
	:module: MidTmcCentralNode

	List of SdpSubarrayLeafNode devices

	:data type: DevVarStringArray

.. index::
	single: SkaLevel; MidTmcCentralNode.SkaLevel

.. py:attribute:: SkaLevel
	:module: MidTmcCentralNode

	:data type: DevShort
	:default value: 4

.. index::
	single: SubarrayPrefix; MidTmcCentralNode.SubarrayPrefix

.. py:attribute:: SubarrayPrefix
	:module: MidTmcCentralNode

	:data type: DevString

.. index::
	single: TMCSubarrayNodes; MidTmcCentralNode.TMCSubarrayNodes

.. py:attribute:: TMCSubarrayNodes
	:module: MidTmcCentralNode

	List of TMC Mid Subarray Node devices

	:data type: DevVarStringArray

Attributes
----------
.. index::
	single: DefaultArrayLayoutURL; MidTmcCentralNode.DefaultArrayLayoutURL

.. py:attribute:: DefaultArrayLayoutURL
	:module: MidTmcCentralNode

	Returns the default array layout URL attribute value.

	:access: READ_WRITE
	:data type: DevString
	:data format: SCALAR

.. index::
	single: arrayLayoutFileProvided; LowTmcCentralNode.arrayLayoutFileProvided

.. py:attribute:: arrayLayoutFileProvided
	:module: LowTmcCentralNode

	Returns the boolean indicating whether the  default array layout URL is provided.

	:access: READ
	:data type: DevBoolean
	:data format: SCALAR

.. index::
	single: DishVccCommandStatus; MidTmcCentralNode.DishVccCommandStatus

.. py:attribute:: DishVccCommandStatus
	:module: MidTmcCentralNode

	Return the DishVccCommandStatus attribute.

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: DishVccValidationStatus; MidTmcCentralNode.DishVccValidationStatus

.. py:attribute:: DishVccValidationStatus
	:module: MidTmcCentralNode

	Return the DishVccValidationStatus

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: GlobalPointingModelStatus; MidTmcCentralNode.GlobalPointingModelStatus

.. py:attribute:: GlobalPointingModelStatus
	:module: MidTmcCentralNode

	Return the GlobalPointingModelStatus attribute.

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: State; MidTmcCentralNode.State

.. py:attribute:: State
	:module: MidTmcCentralNode

	The operational state of the device as enumeration.

	:access: READ
	:data type: DevState
	:data format: SCALAR

.. index::
	single: Status; MidTmcCentralNode.Status

.. py:attribute:: Status
	:module: MidTmcCentralNode

	More detailed textual information about the device's status.

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: adminMode; MidTmcCentralNode.adminMode

.. py:attribute:: adminMode
	:module: MidTmcCentralNode

	The Admin Mode of the device. It may interpret the current device condition and condition of all managed devices to set this. Most possibly an aggregate attribute.

	:access: READ_WRITE
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: arrayLayoutURL; MidTmcCentralNode.arrayLayoutURL

.. py:attribute:: arrayLayoutURL
	:module: MidTmcCentralNode

	Returns the array layout URL attribute value.

	:access: READ_WRITE
	:data type: DevString
	:data format: SCALAR

.. index::
	single: buildState; MidTmcCentralNode.buildState

.. py:attribute:: buildState
	:module: MidTmcCentralNode

	Read the Build State of the device.

	:return: the build state of the device

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: commandTimeOut; MidTmcCentralNode.commandTimeOut

.. py:attribute:: commandTimeOut
	:module: MidTmcCentralNode

	Command execution time limit.

	:access: READ_WRITE
	:data type: DevUShort
	:data format: SCALAR

.. index::
	single: commandedState; MidTmcCentralNode.commandedState

.. py:attribute:: commandedState
	:module: MidTmcCentralNode

	The last commanded Operating State of the device. Initial string is "None".  Only other strings it can change to is "OFF", "STANDBY" or "ON", following the Off(), Standby() or On() commands. If the state transition commands are long running commands the commanded state will only update when the long running command starts executing.

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: controlMode; MidTmcCentralNode.controlMode

.. py:attribute:: controlMode
	:module: MidTmcCentralNode

	The control mode of the device are REMOTE, LOCAL Tango Device accepts only from a ‘local’ client and ignores commands and queries received from TM or any other ‘remote’ clients. The Local clients has to release LOCAL control before REMOTE clients can take control again.

	:access: READ_WRITE
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: desiredTelescopeState; MidTmcCentralNode.desiredTelescopeState

.. py:attribute:: desiredTelescopeState
	:module: MidTmcCentralNode

	desiredTelescopeState attribute of Central Node.

	:access: READ
	:data type: DevState
	:data format: SCALAR

.. index::
	single: healthState; MidTmcCentralNode.healthState

.. py:attribute:: healthState
	:module: MidTmcCentralNode

	Read the Health State of the device. It interprets the current device condition and condition of all managed devices to set this. Most possibly an aggregate attribute.

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: imaging; MidTmcCentralNode.imaging

.. py:attribute:: imaging
	:module: MidTmcCentralNode

	Imaging Attribute

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: internalModel; MidTmcCentralNode.internalModel

.. py:attribute:: internalModel
	:module: MidTmcCentralNode

	Json String representing the entire internal model.

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: isDishVccConfigSet; MidTmcCentralNode.isDishVccConfigSet

.. py:attribute:: isDishVccConfigSet
	:module: MidTmcCentralNode

	Return the isDishVccConfigSet attribute.

	:access: READ
	:data type: DevBoolean
	:data format: SCALAR

.. index::
	single: lastDeviceInfoChanged; MidTmcCentralNode.lastDeviceInfoChanged

.. py:attribute:: lastDeviceInfoChanged
	:module: MidTmcCentralNode

	Json String representing the last device info changed in the             internal model.

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: loggingLevel; MidTmcCentralNode.loggingLevel

.. py:attribute:: loggingLevel
	:module: MidTmcCentralNode

	Read the logging level of the device.

	Initialises to LoggingLevelDefault on startup.
	See :py:class:`~ska_control_model.LoggingLevel`

	:return:  Logging level of the device.

	:access: READ_WRITE
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: loggingTargets; MidTmcCentralNode.loggingTargets

.. py:attribute:: loggingTargets
	:module: MidTmcCentralNode

	Read the additional logging targets of the device.

	Note that this excludes the handlers provided by the ska_ser_logging
	library defaults - initialises to LoggingTargetsDefault on startup.

	:return:  Logging level of the device.

	:access: READ_WRITE
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 4

.. index::
	single: longRunningCommandIDsInQueue; MidTmcCentralNode.longRunningCommandIDsInQueue

.. py:attribute:: longRunningCommandIDsInQueue
	:module: MidTmcCentralNode

	Read the IDs of the long running commands in the queue.

	Every client that executes a command will receive a command ID as response.
	Keep track of IDs currently allocated.
	Entries are removed `self._command_tracker._removal_time` seconds
	after they have finished.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 66

.. index::
	single: longRunningCommandInProgress; MidTmcCentralNode.longRunningCommandInProgress

.. py:attribute:: longRunningCommandInProgress
	:module: MidTmcCentralNode

	Read the name(s) of the currently executing long running command(s).

	Name(s) of command and possible abort in progress or empty string(s).

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 2

.. index::
	single: longRunningCommandProgress; MidTmcCentralNode.longRunningCommandProgress

.. py:attribute:: longRunningCommandProgress
	:module: MidTmcCentralNode

	Read the progress of the currently executing long running command(s).

	ID, progress of the currently executing command(s).
	Clients can subscribe to on_change event and wait
	for the ID they are interested in.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 4

.. index::
	single: longRunningCommandResult; MidTmcCentralNode.longRunningCommandResult

.. py:attribute:: longRunningCommandResult
	:module: MidTmcCentralNode

	Read the result of the completed long running command.

	Reports unique_id, json-encoded result.
	Clients can subscribe to on_change event and wait for
	the ID they are interested in.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 2

.. index::
	single: longRunningCommandStatus; MidTmcCentralNode.longRunningCommandStatus

.. py:attribute:: longRunningCommandStatus
	:module: MidTmcCentralNode

	Read the status of the currently executing long running commands.

	ID, status pairs of the currently executing commands.
	Clients can subscribe to on_change event and wait for the
	ID they are interested in.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 132

.. index::
	single: longRunningCommandsInQueue; MidTmcCentralNode.longRunningCommandsInQueue

.. py:attribute:: longRunningCommandsInQueue
	:module: MidTmcCentralNode

	Read the long running commands in the queue.

	Keep track of which commands are that are currently known about.
	Entries are removed `self._command_tracker._removal_time` seconds
	after they have finished.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 66

.. index::
	single: lrcExecuting; MidTmcCentralNode.lrcExecuting

.. py:attribute:: lrcExecuting
	:module: MidTmcCentralNode

	Expose a signal as a Tango attribute.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 2

.. index::
	single: lrcFinished; MidTmcCentralNode.lrcFinished

.. py:attribute:: lrcFinished
	:module: MidTmcCentralNode

	Expose a signal as a Tango attribute.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 100

.. index::
	single: lrcProtocolVersions; MidTmcCentralNode.lrcProtocolVersions

.. py:attribute:: lrcProtocolVersions
	:module: MidTmcCentralNode

	Return supported protocol versions.

	:return: A tuple containing the lower and upper bounds of supported long running
		command protocol versions.

	:access: READ
	:data type: DevLong64
	:data format: SPECTRUM
	:max_dim_x: 2

.. index::
	single: lrcQueue; MidTmcCentralNode.lrcQueue

.. py:attribute:: lrcQueue
	:module: MidTmcCentralNode

	Expose a signal as a Tango attribute.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 32

.. index::
	single: pss; MidTmcCentralNode.pss

.. py:attribute:: pss
	:module: MidTmcCentralNode

	PSS Attribute

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: pst; MidTmcCentralNode.pst

.. py:attribute:: pst
	:module: MidTmcCentralNode

	PST Attribute

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: simulationMode; MidTmcCentralNode.simulationMode

.. py:attribute:: simulationMode
	:module: MidTmcCentralNode

	When TRUE the device is using a simulator

	:access: READ_WRITE
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: telescopeAvailability; MidTmcCentralNode.telescopeAvailability

.. py:attribute:: telescopeAvailability
	:module: MidTmcCentralNode

	Returns telescope availability

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: telescopeHealthState; MidTmcCentralNode.telescopeHealthState

.. py:attribute:: telescopeHealthState
	:module: MidTmcCentralNode

	Health state of Telescope

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: telescopeState; MidTmcCentralNode.telescopeState

.. py:attribute:: telescopeState
	:module: MidTmcCentralNode

	DevState of telescope

	:access: READ
	:data type: DevState
	:data format: SCALAR

.. index::
	single: testMode; MidTmcCentralNode.testMode

.. py:attribute:: testMode
	:module: MidTmcCentralNode

	If TEST the device is using testing logic

	:access: READ_WRITE
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: tmOpState; MidTmcCentralNode.tmOpState

.. py:attribute:: tmOpState
	:module: MidTmcCentralNode

	Return the tmOpState attribute.

	:access: READ
	:data type: DevState
	:data format: SCALAR

.. index::
	single: transformedInternalModel; MidTmcCentralNode.transformedInternalModel

.. py:attribute:: transformedInternalModel
	:module: MidTmcCentralNode

	Json String representing the entire internal model transformed             for better reading.

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: versionId; MidTmcCentralNode.versionId

.. py:attribute:: versionId
	:module: MidTmcCentralNode

	Read the Version Id of the device.

	:return: the version id of the device

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: vlbi; MidTmcCentralNode.vlbi

.. py:attribute:: vlbi
	:module: MidTmcCentralNode

	VLBI Attribute

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

Commands
--------
.. index::
	single: Abort; MidTmcCentralNode.Abort

.. py:method:: Abort() -> DevVarLongStringArray
	:module: MidTmcCentralNode

	No input parameter (DevVoid)

	:returns: [ResultCode.STARTED][command_id]

.. index::
	single: AbortCommands; MidTmcCentralNode.AbortCommands

.. py:method:: AbortCommands() -> DevVarLongStringArray
	:module: MidTmcCentralNode

	No input parameter (DevVoid)

	:returns: returns (None): A tuple containing a return code and a string
		message indicating status. The message is for
		information purpose only.

.. index::
	single: AssignResources; MidTmcCentralNode.AssignResources

.. py:method:: AssignResources(DevString) -> DevVarLongStringArray
	:module: MidTmcCentralNode

	:param argin: (not documented)

	:type argin: DevString

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: CheckLongRunningCommandStatus; MidTmcCentralNode.CheckLongRunningCommandStatus

.. py:method:: CheckLongRunningCommandStatus(DevString) -> DevString
	:module: MidTmcCentralNode

	command id

	:returns: TaskStatus

.. index::
	single: DebugDevice; MidTmcCentralNode.DebugDevice

.. py:method:: DebugDevice() -> DevUShort
	:module: MidTmcCentralNode

	No input parameter (DevVoid)

	:returns: The TCP port the debugger is listening on.

.. index::
	single: GetVersionInfo; MidTmcCentralNode.GetVersionInfo

.. py:method:: GetVersionInfo() -> DevVarStringArray
	:module: MidTmcCentralNode

	No input parameter (DevVoid)

	:returns: returns (None): The result code and the command unique ID

.. index::
	single: Init; MidTmcCentralNode.Init

.. py:method:: Init() -> DevVoid
	:module: MidTmcCentralNode

	Init

.. index::
	single: LoadDishCfg; MidTmcCentralNode.LoadDishCfg

.. py:method:: LoadDishCfg(DevString) -> DevVarLongStringArray
	:module: MidTmcCentralNode

	:param argin: (not documented)

	:type argin: DevString

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: Off; MidTmcCentralNode.Off

.. py:method:: Off() -> DevVarLongStringArray
	:module: MidTmcCentralNode

	No input parameter (DevVoid)

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: On; MidTmcCentralNode.On

.. py:method:: On() -> DevVarLongStringArray
	:module: MidTmcCentralNode

	No input parameter (DevVoid)

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: ReleaseResources; MidTmcCentralNode.ReleaseResources

.. py:method:: ReleaseResources(DevString) -> DevVarLongStringArray
	:module: MidTmcCentralNode

	:param argin: (not documented)

	:type argin: DevString

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: Reset; MidTmcCentralNode.Reset

.. py:method:: Reset() -> DevVarLongStringArray
	:module: MidTmcCentralNode

	No input parameter (DevVoid)

	:returns: [ResultCode][message or command id]

.. index::
	single: SetGlobalPointingModel; MidTmcCentralNode.SetGlobalPointingModel

.. py:method:: SetGlobalPointingModel(DevString) -> DevVarLongStringArray
	:module: MidTmcCentralNode

	:param argin: (not documented)

	:type argin: DevString

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: SetStowMode; MidTmcCentralNode.SetStowMode

.. py:method:: SetStowMode(DevString) -> DevVarLongStringArray
	:module: MidTmcCentralNode

	:param argin: (not documented)

	:type argin: DevString

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: Standby; MidTmcCentralNode.Standby

.. py:method:: Standby() -> DevVarLongStringArray
	:module: MidTmcCentralNode

	No input parameter (DevVoid)

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: TelescopeOff; MidTmcCentralNode.TelescopeOff

.. py:method:: TelescopeOff() -> DevVarLongStringArray
	:module: MidTmcCentralNode

	No input parameter (DevVoid)

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: TelescopeOn; MidTmcCentralNode.TelescopeOn

.. py:method:: TelescopeOn() -> DevVarLongStringArray
	:module: MidTmcCentralNode

	No input parameter (DevVoid)

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: TelescopeStandby; MidTmcCentralNode.TelescopeStandby

.. py:method:: TelescopeStandby() -> DevVarLongStringArray
	:module: MidTmcCentralNode

	No input parameter (DevVoid)

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray
