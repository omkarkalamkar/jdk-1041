ska\_tmc\_centralnode.manager package
=====================================

Subpackages
-----------

.. toctree::
   :maxdepth: 4

   ska_tmc_centralnode.manager.transition_rules

Submodules
----------

ska\_tmc\_centralnode.manager.aggregators module
------------------------------------------------

.. automodule:: ska_tmc_centralnode.manager.aggregators
   :members:
   :undoc-members:
   :show-inheritance:

ska\_tmc\_centralnode.manager.aggregate\_process module
-------------------------------------------------------

.. automodule:: ska_tmc_centralnode.manager.aggregate_process
   :members:
   :undoc-members:
   :show-inheritance:


ska\_tmc\_centralnode.manager.component\_manager module
-------------------------------------------------------

.. automodule:: ska_tmc_centralnode.manager.component_manager
   :members:
   :undoc-members:
   :show-inheritance:


ska\_tmc\_centralnode.manager.component\_manager\_mid module
------------------------------------------------------------

.. automodule:: ska_tmc_centralnode.manager.component_manager_mid
   :members:
   :undoc-members:
   :show-inheritance:


ska\_tmc\_centralnode.manager.component\_manager\_low module
------------------------------------------------------------

.. automodule:: ska_tmc_centralnode.manager.component_manager_low
   :members:
   :undoc-members:
   :show-inheritance:


ska\_tmc\_centralnode.manager.event\_data\_manager module
---------------------------------------------------------

.. automodule:: ska_tmc_centralnode.manager.event_data_manager
   :members:
   :undoc-members:
   :show-inheritance:


ska\_tmc\_centralnode.manager.event\_manager module
----------------------------------------------------

.. automodule:: ska_tmc_centralnode.manager.event_manager
   :members:
   :undoc-members:
   :show-inheritance:


Module contents
---------------

.. automodule:: ska_tmc_centralnode.manager
   :members:
   :undoc-members:
   :show-inheritance:


Command Timeout
===============

The ``CommandTimeout`` attribute is introduced to allow updating the timeout value
for commands without requiring a redeployment. This provides flexibility in tuning
the timeout dynamically at runtime based on operational needs.

The ``CommandTimeOutDefault`` property is also introduced, which can be used to set
a default timeout value during the deployment phase. This ensures that an initial
timeout value is preconfigured when the component starts for the first time.

Usage
-----

* **CommandTimeout attribute**
  - Can be updated at runtime without redeployment.
  - Helps in adapting to varying command execution times.

* **CommandTimeOutDefault property**
  - Configurable in the deployment configuration (e.g., ``values.yaml``).
  - Sets the initial timeout value at startup.