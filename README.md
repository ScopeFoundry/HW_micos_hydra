ScopeFoundryHW.pi_micos_hydra_tt
=================================

ScopeFoundry hardware plug-in to control a PI/miCos SMC Hydra TT XY stage
controller over its native Venus-3 serial protocol.

ScopeFoundry is a Python platform for controlling custom laboratory
experiments and visualizing scientific data.

<http://www.scopefoundry.org>

This software is not made by or endorsed by the device manufacturer.

Author
------

Tim Kodalle

Requirements
------------

    * ScopeFoundry
    * pyserial

No vendor SDK or DLL is required -- this plug-in talks to the controller
directly over RS-232 (115200 baud, 8N1, no handshake) using the controller's
native Venus-3 command set (see the manufacturer's Hydra TT command
reference manual).

Usage
-----

`MicosHydraTtHW` exposes X/Y position, target, velocity, acceleration, stop
deceleration, and moving/emergency-switch status as ScopeFoundry settings,
plus operations to initialize (enable), home/calibrate, and halt each axis.

The controller powers up with both axes' motors disabled, so
`MicosHydraTtHW.connect()` automatically initializes (enables) both axes on
connect -- no manual "Init" click is needed before a move will work.

Files
-----

    * micos_hydra_venus_dev.py     -- low-level Venus-3 serial driver
    * micos_hydra_venus_hw.py      -- ScopeFoundry HardwareComponent
    * micos_hydra_venus_readout.py -- example Measurement/readout
    * micos_hydra_venus_test_app.py -- minimal standalone test app

Run the test app from a project that has this plug-in and ScopeFoundry
installed:

    python -m ScopeFoundryHW.pi_micos_hydra_tt.micos_hydra_venus_test_app

Known quirks
------------

    * Sending `init` to an axis (including the automatic init-on-connect)
      causes a small (few-micron) physical position nudge on that axis.
      Not currently compensated for -- worth revisiting if your application
      needs micron-level positioning accuracy right after connecting.

History
-------

### 0.1.0    2026-09-03    Initial public release, verified against real Hydra TT hardware.
