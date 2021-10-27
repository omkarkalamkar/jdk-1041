Feature: Central Node acceptance

Scenario: Check internal model according to the TANGO ecosystem deployed
  Given a TANGO ecosystem with a set of devices deployed
  And a CentralNode device called <central_node_name>
  When I get the attribute InternalModel of the CentralNode device
  Then it correctly reports the failed and working devices

Scenario: Run Commands
  Given a CentralNode device called <central_node_name>
  When I call the command <command_name>
  Then the command is queued and executed in less than 5 ss