===================
ReleaseResourcesLow
===================

    1. Central Node provides API for **ReleaseResources workflow**.
    2. Input JSON is as per schema detailed at - https://developer.skao.int/projects/ska-telmodel/en/latest/schemas/tmc/ska-low-tmc-releaseres.html
    3. The Central Node **accepts the command** if :-

        a. Admin mode reported by each of the system - CSP,SDP,MCCS controller are in **ONLINE/ENGINEERING/RESERVED**
        b. Operational state of central node is **ON/OFF/INIT/STANDBY/ALARM**

    4. The Central Node **rejects the command** if :-

        a. Admin mode reported by each of the system - CSP,SDP,MCCS controller are in **OFFLINE** or **NOT FITTED**.
        b. Operational state of central node is **FAULT/UNKNOWN/DISABLE** .

    5. The Input JSON is validated as below, and Command is `'Rejected'` with **exception message if they are not met** :-

        a. JSON should not be empty or malformed
        b. JSON validation against the schema specified in the Telescope Model (https://developer.skao.int/projects/ska-telmodel/en/latest/schemas/tmc/ska-low-tmc-releaseres.html)
    
    6. The following **state requirements** are applied for the **command execution** :-

        a. TMC Subarray is in `'observation state'` **IDLE** .
        b. :term:`telescopeAvailability` is checked to ensure the subsystems (SubarryNode, CSP, SDP and MCCS) are :term:`available`

    7. The command execution involves below key operations :-
        1. `'transaction ID'` is removed from the input JSON
        2. The command is then invoked on the relevant TMC Subarray Node.

            a. If TMC Subarry node **rejects** assign resources command , command failure is reported as **'RESULT_CODE - FAILED'** on Long Running Command Result attribute of the central node.
            b. If TMC Subarry node **accepts** command , central node will wait for command completion.  

    8. The Central Node monitors the progress of command via the subarray ObsState transitions and the long running command results :-

        a. Command is successful when the TMC Subarray Node transitions to **EMPTY** ObsState. This is reported as **'RESULT_CODE - OK'** on Long Running Command Result attribute of the central node.
        b. Command failure is reported in any of the below cases as **'RESULT_CODE - FAILED'** on Long Running Command Result attribute of the central node :-

            * The TMC subarray node reports **'RESULT_CODE - FAILED'** on its Long Running Command Result attribute
            * The command times out if TMC SubarryNode does not transition to **EMPTY** within the timeout period specified by `CommandTimeOutDefault` property specified in helm chart of TMC central node .