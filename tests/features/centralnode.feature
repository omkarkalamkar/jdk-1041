@XTP-3615
Feature: Central Node acceptance

	#Check central node correctly report failed and working devices defined within its scope of monitoring (internal model)
	@XTP-3613 @XTP-3614 @post_deployment @acceptance @SKA_mid @SKA_low
	Scenario Outline: Monitor Telescope Components
		Given a TANGO ecosystem with a set of devices deployed
		And a CentralNode device
		When I get the attribute InternalModel of the CentralNode device
		Then it correctly reports the failed and working devices


	#Test the ability to generically run a a set of commands and that the execution is completed withing 5 seconds.
	@XTP-3612 @XTP-3614 @post_deployment @acceptance @SKA_mid @SKA_low
	Scenario: Ability to run commands on central node
		Given a CentralNode device
		When I call the command <command_name>
		Then the command is queued and executed in less than 5 ss

		Examples:
		| command_name		 |
        | TelescopeOn        |
		| AssignResources    |
		| ReleaseResources   |

