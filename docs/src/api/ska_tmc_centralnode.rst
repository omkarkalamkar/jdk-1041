ska\_tmc\_centralnode package
=============================

Link to the TMC User documentation is `here <https://confluence.skatelescope.org/display/UD/TMC+User+Documentation>`_.

Subpackages
-----------

.. toctree::
   :maxdepth: 4

   ska_tmc_centralnode.commands
   ska_tmc_centralnode.manager
   ska_tmc_centralnode.model
   ska_tmc_centralnode.utils

Submodules
----------

ska\_tmc\_centralnode.central\_node module
------------------------------------------

.. automodule:: ska_tmc_centralnode.central_node
   :members:
   :undoc-members:
   :show-inheritance:

ska\_tmc\_centralnode.central\_node\_low module
-----------------------------------------------

.. automodule:: ska_tmc_centralnode.central_node_low
   :members:
   :undoc-members:
   :show-inheritance:

ska\_tmc\_centralnode.central\_node\_mid module
-----------------------------------------------

.. automodule:: ska_tmc_centralnode.central_node_mid
   :members:
   :undoc-members:
   :show-inheritance:

ska\_tmc\_centralnode.input\_validator module
---------------------------------------------

.. automodule:: ska_tmc_centralnode.input_validator
   :members:
   :undoc-members:
   :show-inheritance:

ska\_tmc\_centralnode.release module
------------------------------------

.. automodule:: ska_tmc_centralnode.release
   :members:
   :undoc-members:
   :show-inheritance:

Module contents
---------------

.. automodule:: ska_tmc_centralnode
   :members:
   :undoc-members:
   :show-inheritance:


##########################
Properties in Central Node
##########################


+-------------------------------+-----------------+--------------------------------------------------------------------------------+
| Property Name                 | Data Type       | Description                                                                    |
+===============================+=================+================================================================================+
| TMCSubarrayNodes              | DevStringArray  | List of TMC Mid Subarray Node devices                                          |
+-------------------------------+-----------------+--------------------------------------------------------------------------------+
| CspMasterLeafNodeFQDN         | DevString       | FQDN of the CSP Master Leaf Node device                                        |
+-------------------------------+-----------------+--------------------------------------------------------------------------------+
| CspMasterFQDN                 | DevString       | FQDN of the CSP Master device                                                  |
+-------------------------------+-----------------+--------------------------------------------------------------------------------+
| SdpMasterLeafNodeFQDN         | DevString       | FQDN of the SDP Master Leaf Node device                                        |
+-------------------------------+-----------------+--------------------------------------------------------------------------------+
| SdpMasterFQDN                 | DevString       | FQDN of the SDP Master device                                                  |
+-------------------------------+-----------------+--------------------------------------------------------------------------------+
| CspSubarrayLeafNodes          | DevStringArray  | List of the CSP Subarray Leaf Node devices                                     |
+-------------------------------+-----------------+--------------------------------------------------------------------------------+
| SdpSubarrayLeafNodes          | DevStringArray  | List of the CSP Subarray Leaf Node devices                                     |
+-------------------------------+-----------------+--------------------------------------------------------------------------------+
| SkuidService                  | DevString       | Default value for SKUID service                                                |
+-------------------------------+-----------------+--------------------------------------------------------------------------------+
| CommandTimeOut                | DevFloat        | Timeout for the command execution                                              |
+-------------------------------+-----------------+--------------------------------------------------------------------------------+
| LivelinessCheckPeriod         | DevFloat        | Period for the liveliness probe to monitor each device in a loop               |
+-------------------------------+-----------------+--------------------------------------------------------------------------------+
| EventSubscriptionCheckPeriod  | DevFloat        | Period for the event subscriber to check the device subscriptions in a loop    |
+-------------------------------+-----------------+--------------------------------------------------------------------------------+


#########################################
Additional Properties in Central Node Mid
#########################################


+-------------------------------------+----------------+--------------------------------------------------------------------------------+
| Property Name                       | Data Type      | Description                                                                    |
+=====================================+================+================================================================================+
| DishIDs                             | DevStringArray | List containing the ids of the dishes available . This property is for         |
|                                     |                | internal use. It needs to be changed only when there is update in the dishes   |
|                                     |                | available/usable.                                                              |
+-------------------------------------+----------------+--------------------------------------------------------------------------------+
| DishLeafNodePrefix                  | DevString      | Device name prefix for Dish Leaf Node. This property is for internal use.      |
+-------------------------------------+----------------+--------------------------------------------------------------------------------+
| DishMasterIdentifier                | DevString      | Device name tag/identifier for Dish Master device. This property is for        |
|                                     |                | internal use.                                                                  |
+-------------------------------------+----------------+--------------------------------------------------------------------------------+
| DishMasterFQDNs                     | DevStringArray | List of Dish Master devices. This property derived from the values of          |
|                                     |                | properties DishIDs and DishMasterIdentifier. It is for internal use.           |
+-------------------------------------+----------------+--------------------------------------------------------------------------------+
| DishVccUri                          | DevString      | Default URI for Dish VCC Configuration.                                        |
+-------------------------------------+----------------+--------------------------------------------------------------------------------+
| DishVccFilePath                     | DevString      | Default file path for Dish VCC Configuration                                   |
+-------------------------------------+----------------+--------------------------------------------------------------------------------+
| EnableDishVccInit                   | DevBoolean     | This property is set to true to load the dish vcc during initialization.       |
+-------------------------------------+----------------+--------------------------------------------------------------------------------+
| DishKvalueAggregationAllowedPercent | DevDouble      | Percentage of the dishes to be considered for DishKValue aggregation.          |
+-------------------------------------+----------------+--------------------------------------------------------------------------------+
| DishVccInitTimeout                  | DevUShort      | Timeout for the dish vcc initialization                                        |
+-------------------------------------+----------------+--------------------------------------------------------------------------------+
| KValueValidRangeUpperLimit          | int            | Upper limit of the valid k-value range                                         |
+-------------------------------------+----------------+--------------------------------------------------------------------------------+
| KValueValidRangelowerLimit          | int            | Lower limit of the valid k-value range                                         |
+-------------------------------------+----------------+--------------------------------------------------------------------------------+


#########################################
Additional Properties in Central Node Low
#########################################


+-------------------------------+---------------+--------------------------------------------------------------------------------+
| Property Name                 | Data Type     | Description                                                                    |
+===============================+===============+================================================================================+
| MCCSMasterLeafNodeFQDN        | DevString     | FQDN of the MCCS Master Leaf Node Tango Device Server                          |
+-------------------------------+---------------+--------------------------------------------------------------------------------+
| MCCSMasterFQDN                | DevString     | FQDN of the MCCS Master device                                                 |
+-------------------------------+---------------+--------------------------------------------------------------------------------+
