============
TelescopeOff
============

1. This is a **longRunningCommand**. The entry point for this command is TMC CentralNodeLow. There is **no input argument** for this command.
2. This command turns the subsystem devices **OFF**. 
3. Once CentralNodeLow receives **OFF** state events from CSP/SDP/MCCS Subsystems, the telescopeState attribute is updated to **OFF** state, and adminMode attribute should be **ONLINE** for MCCS and CSP.
4. If there is an **exception/error** on any of the lower subsystems or TMC devices, the error is propogated to the CentralNodeLow.