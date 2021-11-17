@XTP-3615
Feature: Central Node acceptance

	#Test the ability to generically run a a set of commands and that the execution is completed withing 5 seconds.
	@XTP-3612 @XTP-3614
	Scenario: Ability to run commands on central node
		Given a CentralNode device called <central_node_name>
		When I call the command <command_name>
		Then the command is queued and executed in less than 5 ss	

	#Check central node correctly report failed and working devices defined within its scope of monitoring (internal model)
	@XTP-3613 @XTP-3614
	Scenario Outline: Monitor Telescope Components
		Given a TANGO ecosystem with a set of devices deployed
		And a CentralNode device called <central_node_name>
		When I get the attribute InternalModel of the CentralNode device
		Then it correctly reports the failed and working devices