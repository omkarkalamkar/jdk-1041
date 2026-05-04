==============================
LowTmcCentralNode Tango Device
==============================

    Central Node is a coordinator of the complete Telescope system
    

Properties
----------
.. index::
	single: CommandTimeOutDefault; LowTmcCentralNode.CommandTimeOutDefault

.. py:attribute:: CommandTimeOutDefault
	:module: LowTmcCentralNode

	:data type: DevFloat
	:default value: 30

.. index::
	single: CspMasterFQDN; LowTmcCentralNode.CspMasterFQDN

.. py:attribute:: CspMasterFQDN
	:module: LowTmcCentralNode

	:data type: DevString

.. index::
	single: CspMasterLeafNodeFQDN; LowTmcCentralNode.CspMasterLeafNodeFQDN

.. py:attribute:: CspMasterLeafNodeFQDN
	:module: LowTmcCentralNode

	:data type: DevString

.. index::
	single: CspSubarrayLeafNodes; LowTmcCentralNode.CspSubarrayLeafNodes

.. py:attribute:: CspSubarrayLeafNodes
	:module: LowTmcCentralNode

	List of CspSubarrayLeafNode devices

	:data type: DevVarStringArray

.. index::
	single: DefaultArrayLayoutPath; LowTmcCentralNode.DefaultArrayLayoutPath

.. py:attribute:: DefaultArrayLayoutPath
	:module: LowTmcCentralNode

	Default array layout path within the TelModel data. Example: 'instrument/ska1_mid/layout/mid-layout.json'

	:data type: DevString

.. index::
	single: DefaultArrayLayoutSourceURIs; LowTmcCentralNode.DefaultArrayLayoutSourceURIs

.. py:attribute:: DefaultArrayLayoutSourceURIs
	:module: LowTmcCentralNode

	Default source URIs for the Array Layout. Defines the TelModel repository source(s). Example: ["gitlab://gitlab.com/ska-telescope/ska-telmodel-data?main#tmdata"]

	:data type: DevString

.. index::
	single: EventSubscriptionCheckPeriod; LowTmcCentralNode.EventSubscriptionCheckPeriod

.. py:attribute:: EventSubscriptionCheckPeriod
	:module: LowTmcCentralNode

	:data type: DevFloat
	:default value: 1

.. index::
	single: GroupDefinitions; LowTmcCentralNode.GroupDefinitions

.. py:attribute:: GroupDefinitions
	:module: LowTmcCentralNode

	:data type: DevVarStringArray

.. index::
	single: IsAutoRecoveryEnabled; LowTmcCentralNode.IsAutoRecoveryEnabled

.. py:attribute:: IsAutoRecoveryEnabled
	:module: LowTmcCentralNode

	:data type: DevBoolean

.. index::
	single: LivelinessCheckPeriod; LowTmcCentralNode.LivelinessCheckPeriod

.. py:attribute:: LivelinessCheckPeriod
	:module: LowTmcCentralNode

	:data type: DevFloat
	:default value: 1

.. index::
	single: LoggingLevelDefault; LowTmcCentralNode.LoggingLevelDefault

.. py:attribute:: LoggingLevelDefault
	:module: LowTmcCentralNode

	:data type: DevUShort
	:default value: 4

.. index::
	single: LoggingTargetsDefault; LowTmcCentralNode.LoggingTargetsDefault

.. py:attribute:: LoggingTargetsDefault
	:module: LowTmcCentralNode

	:data type: DevVarStringArray
	:default value: ['tango::logger']

.. index::
	single: MCCSMasterFQDN; LowTmcCentralNode.MCCSMasterFQDN

.. py:attribute:: MCCSMasterFQDN
	:module: LowTmcCentralNode

	:data type: DevString

.. index::
	single: MCCSMasterLeafNodeFQDN; LowTmcCentralNode.MCCSMasterLeafNodeFQDN

.. py:attribute:: MCCSMasterLeafNodeFQDN
	:module: LowTmcCentralNode

	:data type: DevString

.. index::
	single: ProxyTimeout; LowTmcCentralNode.ProxyTimeout

.. py:attribute:: ProxyTimeout
	:module: LowTmcCentralNode

	:data type: DevUShort
	:default value: 500

.. index::
	single: SdpMasterFQDN; LowTmcCentralNode.SdpMasterFQDN

.. py:attribute:: SdpMasterFQDN
	:module: LowTmcCentralNode

	:data type: DevString

.. index::
	single: SdpMasterLeafNodeFQDN; LowTmcCentralNode.SdpMasterLeafNodeFQDN

.. py:attribute:: SdpMasterLeafNodeFQDN
	:module: LowTmcCentralNode

	:data type: DevString

.. index::
	single: SdpSubarrayLeafNodes; LowTmcCentralNode.SdpSubarrayLeafNodes

.. py:attribute:: SdpSubarrayLeafNodes
	:module: LowTmcCentralNode

	List of SdpSubarrayLeafNode devices

	:data type: DevVarStringArray

.. index::
	single: SkaLevel; LowTmcCentralNode.SkaLevel

.. py:attribute:: SkaLevel
	:module: LowTmcCentralNode

	:data type: DevShort
	:default value: 4

.. index::
	single: SubarrayPrefix; LowTmcCentralNode.SubarrayPrefix

.. py:attribute:: SubarrayPrefix
	:module: LowTmcCentralNode

	:data type: DevString

.. index::
	single: TMCSubarrayNodes; LowTmcCentralNode.TMCSubarrayNodes

.. py:attribute:: TMCSubarrayNodes
	:module: LowTmcCentralNode

	List of TMC Mid Subarray Node devices

	:data type: DevVarStringArray

Attributes
----------
.. index::
	single: DefaultArrayLayoutURL; LowTmcCentralNode.DefaultArrayLayoutURL

.. py:attribute:: DefaultArrayLayoutURL
	:module: LowTmcCentralNode

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
	single: State; LowTmcCentralNode.State

.. py:attribute:: State
	:module: LowTmcCentralNode

	The operational state of the device as enumeration.

	:access: READ
	:data type: DevState
	:data format: SCALAR

.. index::
	single: Status; LowTmcCentralNode.Status

.. py:attribute:: Status
	:module: LowTmcCentralNode

	More detailed textual information about the device's status.

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: adminMode; LowTmcCentralNode.adminMode

.. py:attribute:: adminMode
	:module: LowTmcCentralNode

	The Admin Mode of the device. It may interpret the current device condition and condition of all managed devices to set this. Most possibly an aggregate attribute.

	:access: READ_WRITE
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: arrayLayoutURL; LowTmcCentralNode.arrayLayoutURL

.. py:attribute:: arrayLayoutURL
	:module: LowTmcCentralNode

	Returns the array layout URL attribute value.

	:access: READ_WRITE
	:data type: DevString
	:data format: SCALAR

.. index::
	single: assignResourcesSchemaVersion; LowTmcCentralNode.assignResourcesSchemaVersion

.. py:attribute:: assignResourcesSchemaVersion
	:module: LowTmcCentralNode

	Schema version used for AssignResources.

	:access: READ_WRITE
	:data type: DevString
	:data format: SCALAR

.. index::
	single: buildState; LowTmcCentralNode.buildState

.. py:attribute:: buildState
	:module: LowTmcCentralNode

	Read the Build State of the device.

	:return: the build state of the device

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: commandTimeOut; LowTmcCentralNode.commandTimeOut

.. py:attribute:: commandTimeOut
	:module: LowTmcCentralNode

	Command execution time limit.

	:access: READ_WRITE
	:data type: DevUShort
	:data format: SCALAR

.. index::
	single: commandedState; LowTmcCentralNode.commandedState

.. py:attribute:: commandedState
	:module: LowTmcCentralNode

	The last commanded Operating State of the device. Initial string is "None".  Only other strings it can change to is "OFF", "STANDBY" or "ON", following the Off(), Standby() or On() commands. If the state transition commands are long running commands the commanded state will only update when the long running command starts executing.

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: controlMode; LowTmcCentralNode.controlMode

.. py:attribute:: controlMode
	:module: LowTmcCentralNode

	The control mode of the device are REMOTE, LOCAL Tango Device accepts only from a ‘local’ client and ignores commands and queries received from TM or any other ‘remote’ clients. The Local clients has to release LOCAL control before REMOTE clients can take control again.

	:access: READ_WRITE
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: desiredTelescopeState; LowTmcCentralNode.desiredTelescopeState

.. py:attribute:: desiredTelescopeState
	:module: LowTmcCentralNode

	desiredTelescopeState attribute of Central Node.

	:access: READ
	:data type: DevState
	:data format: SCALAR

.. index::
	single: healthState; LowTmcCentralNode.healthState

.. py:attribute:: healthState
	:module: LowTmcCentralNode

	Read the Health State of the device. It interprets the current device condition and condition of all managed devices to set this. Most possibly an aggregate attribute.

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: internalModel; LowTmcCentralNode.internalModel

.. py:attribute:: internalModel
	:module: LowTmcCentralNode

	Json String representing the entire internal model.

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: lastDeviceInfoChanged; LowTmcCentralNode.lastDeviceInfoChanged

.. py:attribute:: lastDeviceInfoChanged
	:module: LowTmcCentralNode

	Json String representing the last device info changed in the             internal model.

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: loggingLevel; LowTmcCentralNode.loggingLevel

.. py:attribute:: loggingLevel
	:module: LowTmcCentralNode

	Read the logging level of the device.

	Initialises to LoggingLevelDefault on startup.
	See :py:class:`~ska_control_model.LoggingLevel`

	:return:  Logging level of the device.

	:access: READ_WRITE
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: loggingTargets; LowTmcCentralNode.loggingTargets

.. py:attribute:: loggingTargets
	:module: LowTmcCentralNode

	Read the additional logging targets of the device.

	Note that this excludes the handlers provided by the ska_ser_logging
	library defaults - initialises to LoggingTargetsDefault on startup.

	:return:  Logging level of the device.

	:access: READ_WRITE
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 4

.. index::
	single: longRunningCommandIDsInQueue; LowTmcCentralNode.longRunningCommandIDsInQueue

.. py:attribute:: longRunningCommandIDsInQueue
	:module: LowTmcCentralNode

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
	single: longRunningCommandInProgress; LowTmcCentralNode.longRunningCommandInProgress

.. py:attribute:: longRunningCommandInProgress
	:module: LowTmcCentralNode

	Read the name(s) of the currently executing long running command(s).

	Name(s) of command and possible abort in progress or empty string(s).

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 2

.. index::
	single: longRunningCommandProgress; LowTmcCentralNode.longRunningCommandProgress

.. py:attribute:: longRunningCommandProgress
	:module: LowTmcCentralNode

	Read the progress of the currently executing long running command(s).

	ID, progress of the currently executing command(s).
	Clients can subscribe to on_change event and wait
	for the ID they are interested in.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 4

.. index::
	single: longRunningCommandResult; LowTmcCentralNode.longRunningCommandResult

.. py:attribute:: longRunningCommandResult
	:module: LowTmcCentralNode

	Read the result of the completed long running command.

	Reports unique_id, json-encoded result.
	Clients can subscribe to on_change event and wait for
	the ID they are interested in.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 2

.. index::
	single: longRunningCommandStatus; LowTmcCentralNode.longRunningCommandStatus

.. py:attribute:: longRunningCommandStatus
	:module: LowTmcCentralNode

	Read the status of the currently executing long running commands.

	ID, status pairs of the currently executing commands.
	Clients can subscribe to on_change event and wait for the
	ID they are interested in.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 132

.. index::
	single: longRunningCommandsInQueue; LowTmcCentralNode.longRunningCommandsInQueue

.. py:attribute:: longRunningCommandsInQueue
	:module: LowTmcCentralNode

	Read the long running commands in the queue.

	Keep track of which commands are that are currently known about.
	Entries are removed `self._command_tracker._removal_time` seconds
	after they have finished.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 66

.. index::
	single: lrcExecuting; LowTmcCentralNode.lrcExecuting

.. py:attribute:: lrcExecuting
	:module: LowTmcCentralNode

	Expose a signal as a Tango attribute.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 2

.. index::
	single: lrcFinished; LowTmcCentralNode.lrcFinished

.. py:attribute:: lrcFinished
	:module: LowTmcCentralNode

	Expose a signal as a Tango attribute.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 100

.. index::
	single: lrcProtocolVersions; LowTmcCentralNode.lrcProtocolVersions

.. py:attribute:: lrcProtocolVersions
	:module: LowTmcCentralNode

	Return supported protocol versions.

	:return: A tuple containing the lower and upper bounds of supported long running
		command protocol versions.

	:access: READ
	:data type: DevLong64
	:data format: SPECTRUM
	:max_dim_x: 2

.. index::
	single: lrcQueue; LowTmcCentralNode.lrcQueue

.. py:attribute:: lrcQueue
	:module: LowTmcCentralNode

	Expose a signal as a Tango attribute.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 32

.. index::
	single: releaseResourcesSchemaVersion; LowTmcCentralNode.releaseResourcesSchemaVersion

.. py:attribute:: releaseResourcesSchemaVersion
	:module: LowTmcCentralNode

	Schema version used for ReleaseResources.

	:access: READ_WRITE
	:data type: DevString
	:data format: SCALAR

.. index::
	single: simulationMode; LowTmcCentralNode.simulationMode

.. py:attribute:: simulationMode
	:module: LowTmcCentralNode

	When TRUE the device is using a simulator

	:access: READ_WRITE
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: telescopeAvailability; LowTmcCentralNode.telescopeAvailability

.. py:attribute:: telescopeAvailability
	:module: LowTmcCentralNode

	Returns telescope availability

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: telescopeHealthState; LowTmcCentralNode.telescopeHealthState

.. py:attribute:: telescopeHealthState
	:module: LowTmcCentralNode

	Health state of Telescope

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: telescopeState; LowTmcCentralNode.telescopeState

.. py:attribute:: telescopeState
	:module: LowTmcCentralNode

	DevState of telescope

	:access: READ
	:data type: DevState
	:data format: SCALAR

.. index::
	single: testMode; LowTmcCentralNode.testMode

.. py:attribute:: testMode
	:module: LowTmcCentralNode

	If TEST the device is using testing logic

	:access: READ_WRITE
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: tmOpState; LowTmcCentralNode.tmOpState

.. py:attribute:: tmOpState
	:module: LowTmcCentralNode

	Return the tmOpState attribute.

	:access: READ
	:data type: DevState
	:data format: SCALAR

.. index::
	single: transformedInternalModel; LowTmcCentralNode.transformedInternalModel

.. py:attribute:: transformedInternalModel
	:module: LowTmcCentralNode

	Json String representing the entire internal model transformed             for better reading.

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: versionId; LowTmcCentralNode.versionId

.. py:attribute:: versionId
	:module: LowTmcCentralNode

	Read the Version Id of the device.

	:return: the version id of the device

	:access: READ
	:data type: DevString
	:data format: SCALAR

Commands
--------
.. index::
	single: Abort; LowTmcCentralNode.Abort

.. py:method:: Abort() -> DevVarLongStringArray
	:module: LowTmcCentralNode

	No input parameter (DevVoid)

	:returns: [ResultCode.STARTED][command_id]

.. index::
	single: AbortCommands; LowTmcCentralNode.AbortCommands

.. py:method:: AbortCommands() -> DevVarLongStringArray
	:module: LowTmcCentralNode

	No input parameter (DevVoid)

	:returns: returns (None): A tuple containing a return code and a string
		message indicating status. The message is for
		information purpose only.

.. index::
	single: AssignResources; LowTmcCentralNode.AssignResources

.. py:method:: AssignResources(DevString) -> DevVarLongStringArray
	:module: LowTmcCentralNode

	:param argin: (not documented)

	:type argin: DevString

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: CheckLongRunningCommandStatus; LowTmcCentralNode.CheckLongRunningCommandStatus

.. py:method:: CheckLongRunningCommandStatus(DevString) -> DevString
	:module: LowTmcCentralNode

	command id

	:returns: TaskStatus

.. index::
	single: DebugDevice; LowTmcCentralNode.DebugDevice

.. py:method:: DebugDevice() -> DevUShort
	:module: LowTmcCentralNode

	No input parameter (DevVoid)

	:returns: The TCP port the debugger is listening on.

.. index::
	single: GetVersionInfo; LowTmcCentralNode.GetVersionInfo

.. py:method:: GetVersionInfo() -> DevVarStringArray
	:module: LowTmcCentralNode

	No input parameter (DevVoid)

	:returns: returns (None): The result code and the command unique ID

.. index::
	single: Init; LowTmcCentralNode.Init

.. py:method:: Init() -> DevVoid
	:module: LowTmcCentralNode

	Init

.. index::
	single: Off; LowTmcCentralNode.Off

.. py:method:: Off() -> DevVarLongStringArray
	:module: LowTmcCentralNode

	No input parameter (DevVoid)

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: On; LowTmcCentralNode.On

.. py:method:: On() -> DevVarLongStringArray
	:module: LowTmcCentralNode

	No input parameter (DevVoid)

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: ReleaseResources; LowTmcCentralNode.ReleaseResources

.. py:method:: ReleaseResources(DevString) -> DevVarLongStringArray
	:module: LowTmcCentralNode

	:param argin: (not documented)

	:type argin: DevString

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: Reset; LowTmcCentralNode.Reset

.. py:method:: Reset() -> DevVarLongStringArray
	:module: LowTmcCentralNode

	No input parameter (DevVoid)

	:returns: [ResultCode][message or command id]

.. index::
	single: Standby; LowTmcCentralNode.Standby

.. py:method:: Standby() -> DevVarLongStringArray
	:module: LowTmcCentralNode

	No input parameter (DevVoid)

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: TelescopeOff; LowTmcCentralNode.TelescopeOff

.. py:method:: TelescopeOff() -> DevVarLongStringArray
	:module: LowTmcCentralNode

	No input parameter (DevVoid)

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: TelescopeOn; LowTmcCentralNode.TelescopeOn

.. py:method:: TelescopeOn() -> DevVarLongStringArray
	:module: LowTmcCentralNode

	No input parameter (DevVoid)

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: TelescopeStandby; LowTmcCentralNode.TelescopeStandby

.. py:method:: TelescopeStandby() -> DevVarLongStringArray
	:module: LowTmcCentralNode

	No input parameter (DevVoid)

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray
