###########
Change Log
###########

All notable changes to this project will be documented in this file.
This project adheres to `Semantic Versioning <http://semver.org/>`_.

[1.0.2]
*******
Updated
-------
* * Update and improvement of log statements across codebase.


[1.0.1]
*******
Updated
-------
* Added notify in observation state change method.

[1.0.0]
********
Updated
-------
* Updated CN to support base class v1.4.0 and pytango v10.1.2.
* Used Signal for attribute wherever required for pushing event.
* Updated is_command_allowed as per new base class.
* Used long_running_command decorator for all commands.

[0.29.2]
*********
Fixed
------
* Fixed SetStowMode timeout error observed on mid integration.

[0.29.1]
*********
Updated
-------
* Updated the PSS validation to reject AssignResourcesLow before queueing in case PSS beams are attempted to be shared between subarrays.

[0.29.0]
*********
Added
-----
* Added SetStowMode command to apply Stow mode on specified dish id's.

[0.28.1]
*********
Updated
-------
* Updated rules for aggregation of telescope health state.

[0.28.0]
*********

Updated
-------
* Updated AssignResources to validate pss beams are not shared between subarrays.

[0.27.0]
*********

Updated
-------
* Central Node now subscribes to the Dish Leaf Node healthState attribute and derives the telescope aggregate health state from it.

[0.26.0]
*********

Updated
-------
* Updates to allow assigning the PST resources (AssignResources schema v2.4)
* Updates to use telescope model v1.28.0

[0.25.1]
*********

Updated
-------
* Updated the TMC mid documentation to bring it on par with the Low updates made towards resolution of skb-808

Added
-----
* Added Tango Resource Locator(TRL) page in knowledge base
* Removed hardcoding of the array layout 

[0.25.0]
********

Fixed
-----
* Fixed the command allowed logic to check the responsiveness flag for specific 
  subarray in case of commands AssignResources and ReleaseResources
* Fixed RTD structure.
* Fixed all the existing docs-build warnings from master.

Added
-----
* Added knowledge base and glossary in RTD.
* Added Command workflow in knowledge base for Subarray Node to resolve comments on SKB-808.
* Added Attribute for Support change ArrayLayout after deployment
* Refactored AssignResources to support arrayLayout 
 
[0.24.3]
********
Updated
-------
Updated imports for the helper device to deploy from ska-tmc-simulators package v1.1.4.

[0.24.2]
********
Updated
-------
* Updated LoadDishCfg method to integrate with the latest command tracker.

[0.24.1]
********
Fixed
-----
* Resolved bug SKB-860

[0.24.0]
********
Added
-----
* Added test case for skb-908.
* Added test case for skb-1051.

Updated
-------
* Updated AssignResources and ReleaseResources commands to use command class id.
* Updated deployment to support 2 subarrays.
* Updated logic to track subsystems assigned per subbarray.
* Updated ska-tmc-common version to 0.34.0

[0.23.0]
********
Added
-----
* Added SetGlobalPointingModel command to apply GPM to specified bands for given dish.
* Added GlobalPointingModelStatus to view the GPM status on dishes.
* Handled GPM initialization and Restart scenarios.

[0.22.0]
********
Added
-----
* Added feature flag as property "IsAutoRecoveryEnabled".

Updated
-------
* Updated the Assign and Release Resources to refrain from invoking command on MCCS leaf node when
  the feature flag is set.
* Removed the SKUID dead code from the repository.

[0.21.3]
********
Fixed
-----
* Dish Vcc Command Status changed to COMPLETED after LoadDishCfg command failure.

[0.21.2]
********
Fixed
-----
* Resolve bug SKB-813
* TelescopeAvailability attribute for mid deployment does not reflect mccs master leafnode availability

[0.21.1]
********
Updated
--------
* Used latest changes from common for CommandTimeout

[0.21.0]
********
Updated
--------
* Updated AssignResources and ReleaseResources commands to work with specified subsystem configurations


[0.20.3]
********
Added
--------
* CommandTimeout attribute is introduced which can help to update timeout without redeployment.
* CommandTimeOutDefault property is introduced which
  can be used to set default value at the time of deployment.
* Update docker with latest base images

[0.20.2]
********
Updated
--------
* Telmodel Download part moved to LoadDishCfg command class to resolve tango corba exception

[0.20.1]
********
Added
------
* Added attribute to update default assign resources interface and release resource interface for low.

Updated
--------
* Telmodel version 1.23.0.
* CDM version 12.10.0.
* Test assign resource jsons to MID v2.2 and LOW v4.1 compatible with SDP v1.0 assign json.

[0.20.0]
********
Added
-----

Added
-----
* Added logic to allow command when the adminmode of subsystems controllers is ONLINE
* Updated common version to 0.27.7

[0.19.7]
********
Added
-------
* Added retry mechanism to device responsiveness check in component manager to fix SKB-860 .

[0.19.6]
********
* Resolved bug SKB-808 on CentralNode

[0.19.5]
********
Updated
-------
* Utilized refactored event manager in central node from v2 in ska-tmc-common
* ska-tmc-common version updated to 0.27.5

[0.19.4]
********
* Utilized the latest common version to 0.27.4
* Added minor changes to loggers.

[0.19.3]
********
* Updated the common version to 0.27.2
* Updated the invoke_command logic to make sure that each failure in Central node command execution is logged.
* Fixed minor bugs in logs on telescope_off_command and telescope_standby_command involving incorrect number of variables provided to parametrized logs.
* Implemented string typecasting in lazy logging to deal with the logging errors involving MemoryError.

[0.19.2]
********
* Updated the common version to 0.26.3
* Fix the failing healthstate test cases

[0.19.1]
********
* Added changes in the logs as per Logging Guidelines
* Added Command ID in logs and fixed logging levels .

[0.19.0]
********
Added
-----
* Added the Rule engine based approach for health state aggregation
* The health state aggregation rule will be running in a seperate process
* AdminMode will be considered for healthstate aggregation.
* Example - If any controller device has adminmode as OFFLINE the healthstate will be degraded.

Update
------
* Updated the ska-tmc-common to v0.25.4 to include master helper leafnode device to set the controller admin mode

Removed
-------
* Old healthstate aggregation code

[0.18.2]
********
* DishVccCommandStatus attribute added for central node
* LoadDishCfg command is rejected if DishVccCommandStatus is STAGING or IN PROGRESS
* After Central Node Initialization complete DishVccCommandStatus changed to COMPLETED or FAILED

[0.18.0]
********
* Tag release with ADR-9 changes

[0.17.7]
********
* Updated event receiver to include state and healthState subscription
* This is branch release and does not include ADR-9 changes


[0.17.6]
********
* Updated FQDNS as per the ADR-9 compliance.


[0.17.5]
********
* Resolved SKB-709 on CentralNode updated checked_device property.

[0.17.4 Defective tag]
**********************
* Inprogress changes of ADR-9 are included.
* Resolved SKB-709 on CentralNode updated checked_device property.

[0.17.3]
********
* Resolved SKB-658 on CentralNode

[0.17.2]
********
* Updated state, health state and load dish config result event receiver with queue mechanism.
* Removed unused attributes from mid and low.

[0.17.1]
********
* Fix telescope ON issue.
* Change event receiver with queue mechanism.

[0.17.0]
********
* Resolved SKB-665 and SKB-525 with updated ska-tmc-common with command callback tracker updates

[0.16.9]
********
* Utilised ska-tmc-common v.0.22.6 with updated received addresses value.

[0.16.8]
********
* Added retry mechanism while downloading tel-model resources to resolve SKB-495.

[0.16.7]
********
* Utilised ska-tmc-common v0.20.2 with liveliness probe updated to track device with full trl.

[0.16.6]
********
* Utilised ska-tmc-common v0.20.0 with liveliness probe changes.

[0.16.5]
********
* Added timeout and error propagation decorators for Assign and Release resources command and Improve logger statements.

[0.16.4]
********
* set and push archive events for all the attributes

[0.16.3]
********
* Fixed long running command result handling in component manager for result code ABORTED

[0.16.2]
********
* Fix long running command result handling in component manager

[0.16.1]
********
* Utilised ska-telmodel v1.17.0
* Updated Assignresources json(interface v.4.0)
* Removed custom validations and added telmodel validation for Assignresources and Releaseresources commands.
* Included base classes v.1.0.0 updates

[0.15.2]
********
* Utilise ska-telmodel v1.17.0
* Update Assignresources json(interface v.4.0)
* Remove custom validations and added telmodel validation for Assignresources and Releaseresources commands.

[0.16.0]
********
* Updated base classes v1.0.0
* Updated control model v1.0.0
* Updated pytango v9.5.0
* Moved the loadDishVccCfg related methods from component manager to Mid component manager.

[0.15.1]
********
* Update Push event mechanism for isDishVccConfigSet , DishVccValidationStatus

[0.15.0]
********
* Update in kValue range from 1-2221 to 1-1177

[0.14.6]
************
* Update CentralNode to work with dish-lmc chart 3.0.0
* Fix the issue about dishes not getting added into monitoring
* Fix issues in the tests

[0.14.5]
************
* Update CentralNode to work with dish-lmc chart 3.0.0

[Main]
******
* Update the .readthedocs.yaml and pyproject.toml file to fix the RTD generation

[0.14.4]
************
* Implement changes for introduced dishMode and pointingState attribute on HelperDishLNDevice

[0.14.3]
************
* Update pytango v9.4.2
* Update ska-tango-base library v0.19.1
* Update ska-tango-base chart v0.4.8
* Update ska-tango-util chart v0.4.10
* Update pylint v3.1.0

[0.1.2]
************