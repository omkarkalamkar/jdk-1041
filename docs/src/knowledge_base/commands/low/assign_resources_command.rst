==================
AssignResourcesLow
==================

The AssignResources command allocates telescope resources to a specific subarray in the SKA-Low telescope configuration.


    1. Central Node provides API for **AssignResources workflow**.

    2. Input JSON is as per schema detailed at - https://developer.skao.int/projects/ska-telmodel/en/latest/schemas/tmc/ska-low-tmc-assignres.html
    3. The Central Node accepts the AssignResources command with a JSON input which specifies the sub-array ID and resource specifications for MCCS, CSP, and SDP.
    4. The Central Node **accepts the command** if :-

        a. Admin mode reported by each of the system - CSP,SDP,MCCS controller are in **ONLINE/ENGINEERING/RESERVED**
        b. Operational state of central node is **ON/OFF/INIT/STANDBY/ALARM**

    5. The Central Node **rejects the command** if :-

        a. Admin mode reported by each of the system - CSP,SDP,MCCS controller are in **OFFLINE** or **NOT FITTED**.
        b. Operational state of central node is **FAULT/UNKNOWN/DISABLE** .

    6. The Input JSON is validated as below, and Command is `'Rejected'` with **exception message if they are not met** :-

        a. JSON should not be empty or malformed
        b. JSON validation against the schema specified in the Telescope Model (https://developer.skao.int/projects/ska-telmodel/en/latest/schemas/tmc/ska-low-tmc-assignres.html)

    7. The following **state requirements** are applied for the **command execution** :-

        a. TMC Subarray is in `'observation state'` **EMPTY** or **IDLE** .
        b. :term:`telescopeAvailability` is checked to ensure the subsystems (SubarryNode, CSP, SDP and MCCS) are :term:`available`
    
    8. The command execution involves below key operations :-
        a. `'transaction ID'` is removed from the input JSON
        b. The command is then invoked on the relevant TMC Subarray Node.

            - If TMC Subarray node **rejects** assign resources command , command failure is reported as **'RESULT_CODE - FAILED'** on Long Running Command Result attribute of the central node.
            - If TMC Subarray node **accepts** command , central node will wait for command completion.  

    9. The Central Node monitors the progress of command via the subarray ObsState transitions and the long running command results :-

        - Command is successful when the TMC Subarray Node transitions to **IDLE** ObsState. This is reported as **'RESULT_CODE - OK'** on Long Running Command Result attribute of the central node.
        - Command failure is reported in any of the below cases as **'RESULT_CODE - FAILED'** on Long Running Command Result attribute of the central node:

            a. The TMC subarray node reports **'RESULT_CODE - FAILED'** on its Long Running Command Result attribute
            b. The **command times out** if TMC SubarrayNode **does not transition** to **IDLE** within the **timeout period** specified by `CommandTimeOutDefault` property specified in helm chart of TMC central node .