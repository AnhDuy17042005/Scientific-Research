from __future__ import annotations

import dataclasses
import enum
import math
import struct
import threading
import time
from typing import Callable, Dict, List, Optional

import can

# --------------------------------------------------------------------------- #
#  Hang so giao thuc
# --------------------------------------------------------------------------- #


class Cmd(enum.IntEnum):
    """cmd_id (5 bit thap cua ID khung CAN)."""
    HEARTBEAT = 0x01              # ODrive -> host, dinh ky
    ESTOP = 0x02                  # host -> ODrive
    GET_MOTOR_ERROR = 0x03        # RTR
    GET_ENCODER_ERROR = 0x04      # RTR
    SET_AXIS_NODE_ID = 0x06
    SET_AXIS_STATE = 0x07
    GET_ENCODER_ESTIMATES = 0x09  # ODrive -> host, dinh ky (hoac RTR)
    GET_ENCODER_COUNT = 0x0A
    SET_CONTROLLER_MODES = 0x0B
    SET_INPUT_POS = 0x0C
    SET_INPUT_VEL = 0x0D
    SET_INPUT_TORQUE = 0x0E
    SET_LIMITS = 0x0F
    SET_TRAJ_VEL_LIMIT = 0x11
    SET_TRAJ_ACCEL_LIMITS = 0x12
    SET_TRAJ_INERTIA = 0x13
    GET_IQ = 0x14                 # RTR
    REBOOT = 0x16
    GET_VBUS_VOLTAGE = 0x17       # RTR
    CLEAR_ERRORS = 0x18


class AxisState(enum.IntEnum):
    UNDEFINED = 0
    IDLE = 1
    STARTUP_SEQUENCE = 2
    FULL_CALIBRATION_SEQUENCE = 3
    MOTOR_CALIBRATION = 4
    ENCODER_INDEX_SEARCH = 6
    ENCODER_OFFSET_CALIBRATION = 7
    CLOSED_LOOP_CONTROL = 8
    LOCKIN_SPIN = 9
    ENCODER_DIR_FIND = 10
    HOMING = 11


class ControlMode(enum.IntEnum):
    VOLTAGE = 0
    TORQUE = 1
    VELOCITY = 2
    POSITION = 3


class InputMode(enum.IntEnum):
    INACTIVE = 0
    PASSTHROUGH = 1     # lenh di thang vao bo dieu khien (khong lam mem)
    VEL_RAMP = 2
    POS_FILTER = 3
    MIX_CHANNELS = 4
    TRAP_TRAJ = 5       # quy dao hinh thang (dung Set_Traj_*)
    TORQUE_RAMP = 6


# Ma loi cua truc (Axis.Error) trong heartbeat, firmware 0.5.x
AXIS_ERRORS = {
    0x00001: "INVALID_STATE",
    0x00040: "MOTOR_FAILED",
    0x00080: "SENSORLESS_ESTIMATOR_FAILED",
    0x00100: "ENCODER_FAILED",
    0x00200: "CONTROLLER_FAILED",
    0x00800: "WATCHDOG_TIMER_EXPIRED",
    0x01000: "MIN_ENDSTOP_PRESSED",
    0x02000: "MAX_ENDSTOP_PRESSED",
    0x04000: "ESTOP_REQUESTED",
    0x20000: "HOMING_WITHOUT_ENDSTOP",
    0x40000: "OVER_TEMP",
    0x80000: "UNKNOWN_POSITION",
}


def decode_axis_error(code: int) -> List[str]:
    """Doi ma loi 32 bit thanh danh sach ten co bit dang bat."""
    names = [n for bit, n in AXIS_ERRORS.items() if code & bit]
    known = 0
    for bit in AXIS_ERRORS:
        known |= bit
    if code & ~known:
        names.append("UNKNOWN(0x%X)" % (code & ~known))
    return names


def state_name(state: int) -> str:
    try:
        return AxisState(state).name
    except ValueError:
        return "STATE_%d" % state


def make_id(node_id: int, cmd: int) -> int:
    return ((node_id & 0x3F) << 5) | (int(cmd) & 0x1F)


def split_id(arbitration_id: int):
    return arbitration_id >> 5, arbitration_id & 0x1F


def _clamp_i16_milli(x: float) -> int:
    """float -> int16 voi do phan giai 0.001 (dinh dang vel_ff / torque_ff)."""
    return max(-32768, min(32767, int(round(x * 1000.0))))


# --------------------------------------------------------------------------- #
#  Phan hoi cua 1 truc
# --------------------------------------------------------------------------- #

@dataclasses.dataclass
class AxisFeedback:
    # --- encoder estimates (0x009) ---
    pos: float = 0.0              # vong
    vel: float = 0.0              # vong/s
    # --- heartbeat (0x001) ---
    axis_error: int = 0
    state: int = 0
    motor_flag: bool = False
    encoder_flag: bool = False
    controller_flag: bool = False
    traj_done: bool = False
    # --- tuy chon, can RTR (0x014, 0x017) ---
    iq_setpoint: float = math.nan  # A
    iq_measured: float = math.nan  # A
    vbus: float = math.nan         # V
    # --- thoi diem (time.monotonic) nhan goi tin gan nhat, 0 = chua tung nhan ---
    t_heartbeat: float = 0.0
    t_encoder: float = 0.0
    t_iq: float = 0.0
    t_vbus: float = 0.0

    @staticmethod
    def _age(t: float) -> float:
        return (time.monotonic() - t) if t > 0.0 else math.inf

    def heartbeat_age(self) -> float:
        return self._age(self.t_heartbeat)

    def encoder_age(self) -> float:
        return self._age(self.t_encoder)


# --------------------------------------------------------------------------- #
#  Bus
# --------------------------------------------------------------------------- #

class CanBus:
    """Quan ly bus CAN + luong nhan. Thread-safe."""

    def __init__(self, interface: str = "socketcan", channel: str = "can0",
                 bitrate: int = 500000):
        kwargs = {"interface": interface, "channel": channel}
        if interface != "socketcan":
            # socketcan: toc do dat bang `ip link ... bitrate ...` (can_up.sh)
            kwargs["bitrate"] = bitrate
        self._bus = can.Bus(**kwargs)
        self._handlers: Dict[int, Callable[[can.Message], None]] = {}
        self._tx_lock = threading.Lock()
        self._stop = threading.Event()
        self.rx_errors = 0
        self.tx_errors = 0
        self._thread = threading.Thread(target=self._rx_loop, name="can-rx",
                                        daemon=True)
        self._thread.start()

    def register(self, node_id: int, handler: Callable[[can.Message], None]):
        self._handlers[node_id] = handler

    def send(self, arbitration_id: int, data: bytes = b"", remote: bool = False):
        msg = can.Message(arbitration_id=arbitration_id,
                          data=b"" if remote else data,
                          is_extended_id=False, is_remote_frame=remote)
        try:
            with self._tx_lock:
                self._bus.send(msg, timeout=0.01)
        except (can.CanError, OSError):
            self.tx_errors += 1

    def _rx_loop(self):
        while not self._stop.is_set():
            try:
                msg = self._bus.recv(0.1)
            except (can.CanError, OSError):
                self.rx_errors += 1
                time.sleep(0.05)
                continue
            if msg is None or msg.is_error_frame or msg.is_extended_id:
                continue
            handler = self._handlers.get(msg.arbitration_id >> 5)
            if handler is not None:
                handler(msg)

    def shutdown(self):
        self._stop.set()
        self._thread.join(timeout=0.5)
        try:
            self._bus.shutdown()
        except Exception:  # noqa: BLE001
            pass


# --------------------------------------------------------------------------- #
#  Truc ODrive
# --------------------------------------------------------------------------- #

class ODriveAxis:
    def __init__(self, bus: CanBus, node_id: int, name: str = ""):
        self.bus = bus
        self.node_id = node_id
        self.name = name or "node%d" % node_id
        self._fb = AxisFeedback()
        self._lock = threading.Lock()
        bus.register(node_id, self._on_message)

    # ------------------------- nhan ------------------------- #
    def _on_message(self, msg: can.Message):
        cmd = msg.arbitration_id & 0x1F
        d = bytes(msg.data)
        now = time.monotonic()
        with self._lock:
            fb = self._fb
            if cmd == Cmd.HEARTBEAT and len(d) >= 5:
                # byte0-3: Axis_Error u32 | byte4: Axis_Current_State u8
                fb.axis_error, fb.state = struct.unpack_from("<IB", d, 0)
                if len(d) >= 8:
                    # Co phu (firmware >= 0.5.2): byte5/6/7 bit0 = co loi motor /
                    # encoder / controller, byte7 bit7 = Trajectory_Done.
                    fb.motor_flag = bool(d[5] & 0x01)
                    fb.encoder_flag = bool(d[6] & 0x01)
                    fb.controller_flag = bool(d[7] & 0x01)
                    fb.traj_done = bool(d[7] & 0x80)
                fb.t_heartbeat = now
            elif cmd == Cmd.GET_ENCODER_ESTIMATES and len(d) >= 8:
                # byte0-3: Pos_Estimate f32 [vong] | byte4-7: Vel_Estimate f32 [vong/s]
                fb.pos, fb.vel = struct.unpack_from("<ff", d, 0)
                fb.t_encoder = now
            elif cmd == Cmd.GET_IQ and len(d) >= 8:
                fb.iq_setpoint, fb.iq_measured = struct.unpack_from("<ff", d, 0)
                fb.t_iq = now
            elif cmd == Cmd.GET_VBUS_VOLTAGE and len(d) >= 4:
                fb.vbus = struct.unpack_from("<f", d, 0)[0]
                fb.t_vbus = now

    def snapshot(self) -> AxisFeedback:
        """Ban sao nhat quan cua phan hoi moi nhat."""
        with self._lock:
            return dataclasses.replace(self._fb)

    def wait_for_data(self, timeout: float = 2.0) -> bool:
        t0 = time.monotonic()
        while time.monotonic() - t0 < timeout:
            fb = self.snapshot()
            if fb.t_heartbeat > 0 and fb.t_encoder > 0:
                return True
            time.sleep(0.02)
        return False

    # ------------------------- gui -------------------------- #
    def _send(self, cmd: int, data: bytes = b"", remote: bool = False):
        self.bus.send(make_id(self.node_id, cmd), data, remote)

    def set_state(self, state: int):
        self._send(Cmd.SET_AXIS_STATE, struct.pack("<I", int(state)))

    def clear_errors(self):
        self._send(Cmd.CLEAR_ERRORS)

    def clear_errors_and_wait(self, timeout: float = 1.5) -> bool:
        """Clear latched errors and wait for a newer clean heartbeat."""
        previous_heartbeat = self.snapshot().t_heartbeat
        self.clear_errors()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            fb = self.snapshot()
            if fb.t_heartbeat > previous_heartbeat and fb.axis_error == 0:
                return True
            time.sleep(0.01)
        return False

    def estop(self):
        self._send(Cmd.ESTOP)

    def reboot(self):
        self._send(Cmd.REBOOT)

    def set_limits(self, vel_limit: float, current_limit: float):
        """Velocity_Limit [vong/s], Current_Limit [A]."""
        self._send(Cmd.SET_LIMITS, struct.pack("<ff", vel_limit, current_limit))

    def set_controller_modes(self, control_mode: int, input_mode: int):
        self._send(Cmd.SET_CONTROLLER_MODES,
                   struct.pack("<ii", int(control_mode), int(input_mode)))

    def set_input_vel(self, vel: float, torque_ff: float = 0.0):
        """Van toc dat [vong/s], momen bu truoc [N*m]."""
        self._send(Cmd.SET_INPUT_VEL, struct.pack("<ff", vel, torque_ff))

    def set_input_pos(self, pos: float, vel_ff: float = 0.0, torque_ff: float = 0.0):
        """Vi tri dat [vong]; vel_ff [vong/s] va torque_ff [N*m] ma hoa int16 x0.001."""
        self._send(Cmd.SET_INPUT_POS,
                   struct.pack("<fhh", pos, _clamp_i16_milli(vel_ff),
                               _clamp_i16_milli(torque_ff)))

    def set_input_torque(self, torque: float):
        self._send(Cmd.SET_INPUT_TORQUE, struct.pack("<f", torque))

    def set_traj_vel_limit(self, vel: float):
        self._send(Cmd.SET_TRAJ_VEL_LIMIT, struct.pack("<f", vel))

    def set_traj_accel_limits(self, accel: float, decel: float):
        self._send(Cmd.SET_TRAJ_ACCEL_LIMITS, struct.pack("<ff", accel, decel))

    # RTR: ODrive tra loi bang khung du lieu cung ID, _on_message se luu lai
    def request_vbus(self):
        self._send(Cmd.GET_VBUS_VOLTAGE, remote=True)

    def request_iq(self):
        self._send(Cmd.GET_IQ, remote=True)

    # ------------------- tien ich muc cao ------------------- #
    def disable(self):
        self.set_input_vel(0.0)
        self.set_state(AxisState.IDLE)

    def start_velocity_control(self, vel_limit: float, current_limit: float,
                               clear_errors: bool = True):
        """Trinh tu an toan de vao che do dieu khien van toc."""
        if clear_errors:
            self.clear_errors()
        self.set_limits(vel_limit, current_limit)
        self.set_controller_modes(ControlMode.VELOCITY, InputMode.PASSTHROUGH)
        self.set_input_vel(0.0)                      # vao closed loop voi van toc 0
        self.set_state(AxisState.CLOSED_LOOP_CONTROL)

    def start_position_control(self, vel_limit: float, current_limit: float,
                               trap: bool = True, traj_vel: float = 1.0,
                               traj_accel: float = 0.5, traj_decel: float = 0.5):
        """Vao che do dieu khien vi tri. Tu dong 'giu' vi tri hien tai de tranh giat
        (input_pos mac dinh = 0 se khien motor lao ve 0 neu khong set truoc)."""
        fb = self.snapshot()
        if fb.t_encoder <= 0.0:
            raise RuntimeError("Chua nhan duoc encoder estimates tu node %d" % self.node_id)
        self.clear_errors()
        self.set_limits(vel_limit, current_limit)
        if trap:
            self.set_traj_vel_limit(traj_vel)
            self.set_traj_accel_limits(traj_accel, traj_decel)
        self.set_controller_modes(
            ControlMode.POSITION,
            InputMode.TRAP_TRAJ if trap else InputMode.PASSTHROUGH)
        self.set_input_pos(fb.pos)
        self.set_state(AxisState.CLOSED_LOOP_CONTROL)


# --------------------------------------------------------------------------- #
#  Giai ma khung de debug (dung trong scripts/decode_can.py)
# --------------------------------------------------------------------------- #

def describe_frame(arbitration_id: int, data: bytes, remote: bool = False) -> str:
    node, cmd = split_id(arbitration_id)
    try:
        name = Cmd(cmd).name
    except ValueError:
        name = "CMD_0x%02X" % cmd
    head = "node=%d %-22s" % (node, name)
    d = bytes(data)
    try:
        if remote:
            return head + "(RTR - yeu cau phan hoi)"
        if cmd == Cmd.HEARTBEAT and len(d) >= 5:
            err, st = struct.unpack_from("<IB", d, 0)
            extra = ""
            if len(d) >= 8:
                extra = " traj_done=%d" % bool(d[7] & 0x80)
            return head + "error=0x%X%s state=%s%s" % (
                err, (" " + ",".join(decode_axis_error(err))) if err else "",
                state_name(st), extra)
        if cmd == Cmd.GET_ENCODER_ESTIMATES and len(d) >= 8:
            p, v = struct.unpack_from("<ff", d, 0)
            return head + "pos=%.4f vong  vel=%.4f vong/s" % (p, v)
        if cmd == Cmd.GET_IQ and len(d) >= 8:
            a, b = struct.unpack_from("<ff", d, 0)
            return head + "Iq_set=%.3f A  Iq_meas=%.3f A" % (a, b)
        if cmd == Cmd.GET_VBUS_VOLTAGE and len(d) >= 4:
            return head + "vbus=%.2f V" % struct.unpack_from("<f", d, 0)
        if cmd == Cmd.SET_AXIS_STATE and len(d) >= 4:
            return head + "state=%s" % state_name(struct.unpack_from("<I", d, 0)[0])
        if cmd == Cmd.SET_CONTROLLER_MODES and len(d) >= 8:
            c, i = struct.unpack_from("<ii", d, 0)
            return head + "control_mode=%d input_mode=%d" % (c, i)
        if cmd == Cmd.SET_INPUT_VEL and len(d) >= 8:
            v, t = struct.unpack_from("<ff", d, 0)
            return head + "vel=%.4f vong/s  torque_ff=%.3f" % (v, t)
        if cmd == Cmd.SET_INPUT_POS and len(d) >= 8:
            p, vf, tf = struct.unpack_from("<fhh", d, 0)
            return head + "pos=%.4f vong  vel_ff=%.3f  torque_ff=%.3f" % (
                p, vf / 1000.0, tf / 1000.0)
        if cmd == Cmd.SET_LIMITS and len(d) >= 8:
            v, c = struct.unpack_from("<ff", d, 0)
            return head + "vel_limit=%.2f vong/s  current_limit=%.2f A" % (v, c)
    except struct.error:
        pass
    return head + "data=" + d.hex(" ")
