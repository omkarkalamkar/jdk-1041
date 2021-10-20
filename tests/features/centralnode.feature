Feature: Central Node acceptance

@post_deployment
@acceptance
Scenario: Check internal model according to the TANGO ecosystem deployed
  Given a TANGO ecosystem with a set of devices deployed
  And a CentralNode device called "ska_mid/tm_central/central_node"
  When I get the attribute InternalModel of the CentralNode device
  Then it correctly reports the failed and working devices

@post_deployment
@acceptance
Scenario: Run On command
  Given a CentralNode device called "ska_mid/tm_central/central_node"
  When I call the command "On" 
  Then the command is queued and executed in less than 5 ss

@post_deployment
@acceptance
Scenario: Run Off command
  Given a CentralNode device called "ska_mid/tm_central/central_node"
  When I call the command "Off" 
  Then the command is queued and executed in less than 5 ss

@post_deployment
@acceptance
Scenario: Run Standby command
  Given a CentralNode device called "ska_mid/tm_central/central_node"
  When I call the command "Standby" 
  Then the command is queued and executed in less than 5 ss

@post_deployment
@acceptance
Scenario: Run StartUpTelescope command
  Given a CentralNode device called "ska_mid/tm_central/central_node"
  When I call the command "StartUpTelescope" 
  Then the command is queued and executed in less than 5 ss

@post_deployment
@acceptance
Scenario: Run StandByTelescope command
  Given a CentralNode device called "ska_mid/tm_central/central_node"
  When I call the command "StandByTelescope" 
  Then the command is queued and executed in less than 5 ss

@post_deployment
@acceptance
Scenario: Run TelescopeStandby command
  Given a CentralNode device called "ska_mid/tm_central/central_node"
  When I call the command "TelescopeStandby" 
  Then the command is queued and executed in less than 5 ss
