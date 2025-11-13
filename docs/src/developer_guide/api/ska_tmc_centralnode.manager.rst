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

Array Layout URL
=================

The ``DefaultArrayLayoutURL`` attribute is introduced to define the default array
layout configuration used by the Central Node. This attribute specifies the default
array layout source and path that the system will use at startup or when no specific
layout is provided.

The ``ArrayLayoutURL`` attribute is introduced to indicate the current array layout
configuration actively in use by the Central Node. This allows dynamic updates to
the array layout at runtime without requiring a redeployment, providing flexibility
for testing or operational adjustments.


# Array Layout URL

The `DefaultArrayLayoutURL` attribute is introduced to define the default array
layout configuration used by the Central Node. This attribute specifies the default
array layout source and path that the system will use at startup or when no specific
layout is provided.

The `ArrayLayoutURL` attribute is introduced to indicate the current array layout
configuration actively in use by the Central Node. This allows dynamic updates to
the array layout at runtime without requiring a redeployment, providing flexibility
for testing or operational adjustments.

## DefaultArrayLayoutSourceURIs

The `DefaultArrayLayoutSourceURIs` device property defines the default source URIs
for the Array Layout. It specifies the TelModel repository source(s).

**Example:**

```
["gitlab://gitlab.com/ska-telescope/ska-telmodel-data?main#tmdata"]
```

ka-telescope/ska-telmodel-data?main#tmdata

```

## DefaultArrayLayoutPath

The ``DefaultArrayLayoutPath`` device property defines the default array layout path
within the TelModel data.

**Example:**
```

instrument/ska1_mid/layout/mid-layout.json

```

**Default value:**
```

instrument/ska1_mid/layout/mid-layout.json

```
```



