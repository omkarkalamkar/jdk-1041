###########
Change Log
###########

All notable changes to this project will be documented in this file.
This project adheres to `Semantic Versioning <http://semver.org/>`_.
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