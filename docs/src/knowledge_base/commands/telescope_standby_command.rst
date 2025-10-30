================
TelescopeStandby
================

1. This is a **longRunningCommand**. The entry point for this command is TMC CentralNodeLow. 
2. There is **no input argument** for this command. This command turns the subsystem devices in **STANDBY** state.
3. Once CentralNodeLow receives **STANDBY** state event from one of the CSP/SDP/MCCS Subsystems, the telescopeState attribute is updated to **STANDBY** state.
4. If there is an **exception/error** on any of the lower subsystems or TMC devices, the **error is propogated to the CentralNodeLow**.