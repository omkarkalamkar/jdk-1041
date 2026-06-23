==============
loaddishcfgMid
==============

The LoadDishCfg command applies the Dish VCC configuration to the specified dishes using the provided JSON input and CSP Master device.
    1. Central Node provides an API for the **LoadDishCfg workflow**.
    2. The **input JSON** must conform to the schema: https://schema.skao.int/ska-mid-cbf-initsysparam/1.0
    3. The Central Node accepts the **LoadDishCfg** command with a JSON input that specifies the Dish VCC paths for the CSP Master and K-values for dish IDs.
    4. The Central Node accepts the command if:
        A. CSP master/controller is in admin mode ONLINEand its state is DevState.OFF.

    5. The **Input JSON** is validated as below, and Command is `'Rejected'` with **exception message if they are not met** :-

        A. JSON should not be empty or malformed
        B. The JSON must contain **interface**, **tm_data_sources** and **tm_data_filepath** with valid values and syntax.

    6. If the command execution fails, subsequent commands on Subarrays will be rejected.

    7. Partial success for setting **K-values** is allowed. However, if the command **fails on the CSP Master leaf node**, the command is **treated as failed**.

    8. The **command execution** involves below **key operations** :-

        A. Checking that the CSP Master is in the required state and admin mode.
        B. Checking that all specified dishes are available.
        C. If the command is successful on the CSP Master leaf node and at least one dish, it is treated as successful.
        D. If the command fails on the CSP Master leaf node, it is treated as unsuccessful.

    9. The Central Node **monitors the progress** of the command using:

        A. Long running command results
        B. Events from K-value validation and CSP Master leaf node Dish VCC validation.

    10. The **DishVccValidationStatus** attribute provides the current status of Dish VCC validation.

    11. The **isDishVccConfigSet** attribute indicates whether the command(AssignResources, ReleaseResources, On, etc) is allowed to execute on TMC.

    12. **Example input JSON**:

    .. code-block:: json

        {
            "interface": "https://schema.skao.int/ska-mid-cbf-initsysparam/1.0",
            "tm_data_sources": [
                "car://gitlab.com/ska-telescope/ska-tmc/ska-tmc-simulators?main#tmdata"
            ],
            "tm_data_filepath": "instrument/dishid_vcc_map_configuration/ska-mid-cbf-system-parameters-mkt.json"
        }



        