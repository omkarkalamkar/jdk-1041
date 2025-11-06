==================
AssignResourcesMid
==================

The AssignResources command allocates telescope resources to a specific subarray in the SKA-Mid telescope configuration.

    1. Central Node provides API for **AssignResources workflow**.
    2. **Input JSON** is as per schema detailed at - https://developer.skao.int/projects/ska-telmodel/en/latest/schemas/tmc/ska-tmc-assignresources.html
    3. The Central Node accepts the AssignResources command with a JSON input which specifies the sub-array ID and resource specifications for CSP, and SDP.
    4. The Central Node **accepts the command** if :-

        A. **Admin mode** reported by each of the system - CSP,SDP are in **ONLINE/ENGINEERING/RESERVED**
        B. **is_dish_vcc_config_set** should be set to **True**
        C. Operational **state** of central node is **ON/OFF/INIT/STANDBY/ALARM**

    5. The Central Node **rejects the command** if :-

        A. Admin mode reported by each of the system - CSP,SDP are in **OFFLINE** or **NOT FITTED**.
        B. **is_dish_vcc_config_set** should be  set to **False**
        C. Operational state of central node is **FAULT/UNKNOWN/DISABLE** .

    6. The **Input JSON** is validated as below, and Command is `'Rejected'` with **exception message if they are not met** :-

        A. **JSON** should not be empty or malformed
        B. **JSON validation** is done with **ska-tmc-cdm**

    7. The following **state requirements** are applied for the **command execution** :-

        A. TMC Subarray is in `'observation state'` **EMPTY** or **IDLE** .
        B. :term:`telescopeAvailability` is checked to ensure the subsystems (SubarrayNode, CSP and SDP) are :term:`available`

    8. The **command execution** involves below **key operations** :-

        A. `'transaction ID'` is removed from the **input JSON**
        B. Check is done to **verify dishes** which are getting **assigned** are **not already assigned** to any of the Subarray.
        C. The command is then invoked on the relevant TMC Subarray Node.

            - If TMC Subarray node **rejects** assign resources command , command failure is reported as **'RESULT_CODE - FAILED'** on Long Running Command Result attribute of the central node.
            - If TMC Subarry node **accepts** command , central node will wait for command completion.

    9. The Central Node **monitors the progress** of command via the **subarray ObsState transitions** and the **long running command results**.

        A. Command is **successful** when the TMC Subarray Node transitions to **IDLE** ObsState. This is reported as **'RESULT_CODE - OK'** on Long Running Command Result attribute of the central node.
        B. Command **failure** is reported in any of the below cases as **'RESULT_CODE - FAILED'** on Long Running Command Result attribute of the central node.

            - The TMC subarray node reports **'RESULT_CODE - FAILED'** on its Long Running Command Result attribute
            - The command times out if TMC SubarrayNode **does not transition to IDLE within the timeout period** specified by `CommandTimeOutDefault` property specified in helm chart of TMC central node .