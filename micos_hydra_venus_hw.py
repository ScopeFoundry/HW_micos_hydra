'''
Created on Aug 21, 2026

@author: Tim Kodalle
'''

from qtpy import QtCore

from ScopeFoundry.hardware import HardwareComponent


class MicosHydraTtHW(HardwareComponent):
    """ScopeFoundry hardware component for the PI/miCos SMC Hydra TT XY stage
    controller (Venus-3 protocol). See SMC-Hydra_CM_TT_RM.pdf in this folder
    for the command reference this is based on."""

    name = "micos_hydra_venus"

    def __init__(self, app, debug=False, name=None,
                 x_axis=1, y_axis=2,
                 invert_x=False, invert_y=False):
        # Hydra axis ids are 1-based in the manual's examples (unlike the
        # Pollux/Venus-2 driver, which defaults to 0-based axis numbers).
        self.x_axis = x_axis
        self.y_axis = y_axis
        self.invert_x = invert_x
        self.invert_y = invert_y
        HardwareComponent.__init__(self, app, debug=debug, name=name)

    def setup(self):
        s = self.settings

        s.New("port", str, initial="COM3", description='COMx, see device manager')
        s.New("baudrate", int, initial=115200)  # default per manual sec. 3

        xy_kwargs = dict(dtype=float, unit='mm', spinbox_decimals=5, spinbox_step=0.1)

        s.New('x_position', ro=True, initial=0.0, **xy_kwargs)
        s.New('y_position', ro=True, initial=0.0, **xy_kwargs)

        s.New('x_moving', dtype=bool, ro=True, initial=False)
        s.New('y_moving', dtype=bool, ro=True, initial=False)

        s.New('x_target', ro=False, initial=0.0, **xy_kwargs)
        s.New('y_target', ro=False, initial=0.0, **xy_kwargs)

        s.New('velocity_x', dtype=float, ro=False, initial=1.0,
              unit='mm/s', spinbox_decimals=3, vmin=0.0)
        s.New('velocity_y', dtype=float, ro=False, initial=1.0,
              unit='mm/s', spinbox_decimals=3, vmin=0.0)

        s.New('acceleration_x', dtype=float, ro=False, initial=10.0,
              unit='mm/s^2', spinbox_decimals=3, vmin=0.0)
        s.New('acceleration_y', dtype=float, ro=False, initial=10.0,
              unit='mm/s^2', spinbox_decimals=3, vmin=0.0)

        # Hydra has no "deceleration during a normal move" concept --
        # setstopdecel only applies to a commanded stop or limit-switch event.
        # Named separately so it isn't confused with a per-move parameter.
        s.New('stop_deceleration_x', dtype=float, ro=False, initial=10.0,
              unit='mm/s^2', spinbox_decimals=3, vmin=0.0)
        s.New('stop_deceleration_y', dtype=float, ro=False, initial=10.0,
              unit='mm/s^2', spinbox_decimals=3, vmin=0.0)

        s.New('emergency_switch_active', dtype=bool, ro=True, initial=False)

        self.add_operation("Init X (enable axis)", self.init_x)
        self.add_operation("Init Y (enable axis)", self.init_y)
        self.add_operation("Init XY", self.init_xy)
        self.add_operation("Calibrate X", self.calibrate_x)
        self.add_operation("Calibrate Y", self.calibrate_y)
        self.add_operation("Calibrate XY", self.calibrate_xy)
        self.add_operation("Halt XY", self.halt_xy)

        self.update_timer = QtCore.QTimer()
        self.update_timer.timeout.connect(self.on_update_timer)

    def connect(self):
        S = self.settings

        from .micos_hydra_venus_dev import MicosHydraTtDev
        self.dev = MicosHydraTtDev(port=S['port'], baudrate=S['baudrate'],
                                    debug=S['debug_mode'])

        S.x_position.connect_to_hardware(read_func=self.read_pos_x)
        S.y_position.connect_to_hardware(read_func=self.read_pos_y)

        S.x_moving.connect_to_hardware(read_func=self.read_x_moving)
        S.y_moving.connect_to_hardware(read_func=self.read_y_moving)

        S.emergency_switch_active.connect_to_hardware(
            read_func=self.dev.get_emergency_switch)

        try:
            S.x_position.read_from_hardware()
            S.y_position.read_from_hardware()
        except Exception as err:
            print('Cannot read XY position:', err)

        S['x_target'] = S['x_position']
        S['y_target'] = S['y_position']
        S.x_target.connect_to_hardware(write_func=self.move_x)
        S.y_target.connect_to_hardware(write_func=self.move_y)

        S.velocity_x.connect_to_hardware(
            write_func=lambda v: self.dev.set_velocity(v, self.x_axis),
            read_func=lambda: self.dev.get_velocity(self.x_axis))
        S.velocity_y.connect_to_hardware(
            write_func=lambda v: self.dev.set_velocity(v, self.y_axis),
            read_func=lambda: self.dev.get_velocity(self.y_axis))
        S.velocity_x.read_from_hardware()
        S.velocity_y.read_from_hardware()

        S.acceleration_x.connect_to_hardware(
            write_func=lambda v: self.dev.set_acceleration(v, self.x_axis),
            read_func=lambda: self.dev.get_acceleration(self.x_axis))
        S.acceleration_y.connect_to_hardware(
            write_func=lambda v: self.dev.set_acceleration(v, self.y_axis),
            read_func=lambda: self.dev.get_acceleration(self.y_axis))
        S.acceleration_x.read_from_hardware()
        S.acceleration_y.read_from_hardware()

        S.stop_deceleration_x.connect_to_hardware(
            write_func=lambda v: self.dev.set_stop_deceleration(v, self.x_axis),
            read_func=lambda: self.dev.get_stop_deceleration(self.x_axis))
        S.stop_deceleration_y.connect_to_hardware(
            write_func=lambda v: self.dev.set_stop_deceleration(v, self.y_axis),
            read_func=lambda: self.dev.get_stop_deceleration(self.y_axis))
        S.stop_deceleration_x.read_from_hardware()
        S.stop_deceleration_y.read_from_hardware()

        # controller powers up with motors off; enable both axes so moves
        # work immediately without a manual Init operation
        self.init_xy()

        self.update_timer.start(1000)

    def disconnect(self):
        if not hasattr(self, 'dev'):
            return

        self.update_timer.stop()
        self.settings.disconnect_all_from_hardware()
        self.dev.close()
        del self.dev

    def on_update_timer(self):
        if not self.settings['connected']:
            return
        try:
            self.settings.x_position.read_from_hardware()
            self.settings.y_position.read_from_hardware()
            self.settings.x_moving.read_from_hardware()
            self.settings.y_moving.read_from_hardware()
        except Exception as err:
            if self.settings['debug_mode']:
                print(f"Error reading position/status: {err}")

        if self.settings['x_moving'] or self.settings['y_moving']:
            self.update_timer.setInterval(100)
        else:
            self.update_timer.setInterval(1000)

    # position
    def read_pos_x(self):
        pos = self.dev.get_position(self.x_axis)
        return -pos if self.invert_x else pos

    def read_pos_y(self):
        pos = self.dev.get_position(self.y_axis)
        return -pos if self.invert_y else pos

    # moving status
    def read_x_moving(self):
        return self.dev.is_moving(self.x_axis)

    def read_y_moving(self):
        return self.dev.is_moving(self.y_axis)

    # moves
    def move_x(self, target):
        if self.invert_x:
            target = -target
        self.dev.nmove(target, self.x_axis)

    def move_y(self, target):
        if self.invert_y:
            target = -target
        self.dev.nmove(target, self.y_axis)

    # operations
    def init_x(self):
        self.dev.init_axis(self.x_axis)

    def init_y(self):
        self.dev.init_axis(self.y_axis)

    def init_xy(self):
        self.init_x()
        self.init_y()

    def calibrate_x(self):
        self.dev.ncal(self.x_axis)

    def calibrate_y(self):
        self.dev.ncal(self.y_axis)

    def calibrate_xy(self):
        self.calibrate_x()
        self.calibrate_y()

    def halt_xy(self):
        self.dev.nabort(self.x_axis)
        self.dev.nabort(self.y_axis)
