=========
Glossary
=========

.. glossary::

    available
        To determine if the subsystem is available, currently TMC calls the state() method on the Tango device proxy to check the device's current state.
        This is a network operation and will fail if the device is unreachable. TMC Central Node reports the availability of an attribute - :term:`telescopeAvailability`.

    telescopeAvailability
            It consists of -

            #. sub-array Availability (as reported by the respective sub-array nodes)
            #. CSP Master availability (as reported by the CSP master leaf node)
            #. SDP Master availability (as reported by the SDP master leaf node)

            In case of Low it also consists: MCCS Master availability ( as reported by the MCCS master leaf node)

    TRL
        It stands for Tango Resource Locator. Check `ADR-9 <https://confluence.skatelescope.org/display/SWSI/ADR-9+Update+naming+conventions+for+TANGO+Devices+and+Servers>`_ for more details.