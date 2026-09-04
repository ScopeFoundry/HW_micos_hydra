
'''
Created on Aug 21, 2026

@author: Tim Kodalle
'''


import serial
import time

NEWLINE = "\r\n"  # confirmed against real Hydra TT controller; plain "\r" gets no reply


class MicosHydraTtDev:

    def __init__(self,
                 port="COM3",  # on windows see device manager
                 baudrate=115200,
                 debug=False):

        self.port = port
        self.debug = debug

        bytesize = 8
        parity = 'N'
        stopbits = 1
        xonxoff = False
        rtscts = False 

        timeout = 1.0

        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=bytesize,
            parity=parity,
            stopbits=stopbits,
            xonxoff=xonxoff,
            rtscts=rtscts,
            timeout=timeout
        )

    def write(self, cmd: str):
        if self.debug:
            print("write:", repr(cmd))
        self.ser.write((cmd + NEWLINE).encode())

    def query(self, cmd: str):
        self.write(cmd)
        time.sleep(0.01)
        resp: bytes = self.ser.readline()
        if self.debug:
            print("resp:", resp.decode())
        return resp.decode()

    def close(self):
        self.ser.close()

    # ==========================================
    # MOVE COMMANDS
    # Hydra/Venus-3 commands are non-blocking -- they return immediately,
    # poll is_moving() to know when a move has finished (manual sec. 9.1).
    # ==========================================

    def nmove(self, position: float, axis: int):
        """Move axis to absolute position. Venus-3 syntax: [position] [axisid] nmove"""
        self.write(f"{position:.6f} {axis} nmove")

    def nrmove(self, distance: float, axis: int):
        """Move axis relative to current position. Venus-3 syntax: [distance] [axisid] nrmove"""
        self.write(f"{distance:.6f} {axis} nrmove")

    def nabort(self, axis: int):
        """Stop a move on one axis. Venus-3 syntax: [axisid] nabort"""
        self.write(f"{axis} nabort")

    def emergency_stop(self):
        """Stop all connected axes (Ctrl-C)."""
        self.write("\x03")

    def ncal(self, axis: int):
        """Home axis (search limit reverse). Venus-3 syntax: [axisid] ncal"""
        self.write(f"{axis} ncal")

    def nrangemeasure(self, axis: int):
        """Range measure (search limit forward). Venus-3 syntax: [axisid] nrm"""
        self.write(f"{axis} nrm")

    def init_axis(self, axis: int):
        """(Re-)enable an axis, e.g. after an error or after releasing an
        emergency-stop. Venus-3 syntax: [axisid] init"""
        self.write(f"{axis} init")

    # ==========================================
    # POSITION / STATUS (read)
    # ==========================================

    def get_position(self, axis: int) -> float:
        """Venus-3 syntax: [axisid] np
        NOTE: on Hydra, 'np' returns ONE axis' position -- unlike the
        Pollux/Venus-2 driver, where 'np' (no args) returns all axes and
        'npos' returns one axis."""
        return float(self.query(f"{axis} np"))

    def get_all_positions(self) -> str:
        """Venus-3 syntax: p -- returns positions of axis 1 & 2."""
        return self.query("p")

    def get_status(self, axis: int) -> int:
        """Venus-3 syntax: [axisid] nst. Returns a decimal status code.
        Manual sec. 7.12.4 documents bit7 (1=stopped by emergency input),
        bit8 (1=motor off), bit9 (1=enable-input open) for the
        hardware-enable feature. Bit0 (move in progress, Venus-2/Pollux
        convention) confirmed against real Hydra TT hardware: reads 1
        during an nrmove/nmove and clears once the move completes."""
        return int(self.query(f"{axis} nst"))

    def is_moving(self, axis: int) -> bool:
        """Bit0 of nstatus; confirmed against real hardware (see get_status)."""
        return bool(self.get_status(axis) & 0b1)

    def is_emergency_stopped(self, axis: int) -> bool:
        """Bit7 of nstatus: 1 = stopped by emergency input (manual sec. 7.12.4)."""
        return bool(self.get_status(axis) & (1 << 7))

    def get_version(self) -> str:
        return self.query("version")

    def get_identify(self) -> str:
        return self.query("identify")

    # ==========================================
    # VELOCITY / ACCELERATION
    # ==========================================

    def set_velocity(self, velocity: float, axis: int):
        """Venus-3 syntax: [velocity] [axisid] setnvel"""
        self.write(f"{velocity} {axis} setnvel")

    def get_velocity(self, axis: int) -> float:
        return float(self.query(f"{axis} getnvel"))

    def set_acceleration(self, acceleration: float, axis: int):
        """Venus-3 syntax: [accel] [axisid] setnaccel
        NOTE: named 'setnaccel' on Hydra, not 'setnacc' like on the
        Pollux/Venus-2 driver."""
        self.write(f"{acceleration} {axis} setnaccel")

    def get_acceleration(self, axis: int) -> float:
        return float(self.query(f"{axis} getnaccel"))

    def set_stop_deceleration(self, deceleration: float, axis: int):
        """Deceleration used for a commanded stop or limit-switch activation.
        Venus-3 syntax: [decel] [axisid] setstopdecel
        NOTE: Hydra has no separate "deceleration during a normal move"
        command -- this is the closest equivalent to Pollux's setndec, but
        semantically different (only applies to stop/limit events)."""
        self.write(f"{deceleration} {axis} setstopdecel")

    def get_stop_deceleration(self, axis: int) -> float:
        return float(self.query(f"{axis} getstopdecel"))

    # ==========================================
    # EMERGENCY INPUT / HARDWARE ENABLE (manual sec. 7.12.4)
    # ==========================================

    def get_emergency_switch(self) -> bool:
        """0 = deactivated, 1 = active"""
        return bool(int(self.query("getemsw")))

    def set_emergency_switch(self, enable: bool):
        self.write(f"{int(enable)} setemsw")

    # ==========================================
    # STORAGE
    # ==========================================

    def save_axis(self, axis: int):
        self.write(f"{axis} nsave")

    def save(self):
        self.write("save")


if __name__ == '__main__':
    print('start')
    dev = MicosHydraTtDev(port="COM3", 
                          debug=True)

    print("version:", dev.get_version())
    print("emergency switch active:", dev.get_emergency_switch())
    print("axis 1 position:", dev.get_position(1))
    print("axis 1 status:", dev.get_status(1))

    dev.close()
    print('done')
