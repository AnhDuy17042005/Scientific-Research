from __future__ import annotations

import math
from typing import Optional, Tuple


def wrap_angle(a: float) -> float:
    return math.atan2(math.sin(a), math.cos(a))


class DiffDrive:
    def __init__(self, wheel_radius: float, track_width: float,
                 gear_ratio: float = 1.0,
                 invert_left: bool = False, invert_right: bool = False):
        if wheel_radius <= 0 or track_width <= 0 or gear_ratio <= 0:
            raise ValueError("wheel_radius, track_width, gear_ratio phai > 0")
        self.R = wheel_radius
        self.L = track_width
        self.gear = gear_ratio                    
        self.sign_left = -1.0 if invert_left else 1.0
        self.sign_right = -1.0 if invert_right else 1.0

        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0
        self._last: Optional[Tuple[float, float]] = None

    @property
    def meters_per_motor_turn(self) -> float:
        return 2.0 * math.pi * self.R / self.gear

    # ---------------- lenh: (v, w) -> vong/s cua motor ---------------- #
    def twist_to_motor_turns(self, v: float, w: float) -> Tuple[float, float]:
        vl = v - w * self.L / 2.0
        vr = v + w * self.L / 2.0
        k = 1.0 / self.meters_per_motor_turn
        return self.sign_left * vl * k, self.sign_right * vr * k

    # ---------------- phan hoi: vong/s cua motor -> (v, w) ------------- #
    def motor_turns_to_twist(self, left_vel: float, right_vel: float) -> Tuple[float, float]:
        m = self.meters_per_motor_turn
        vl = self.sign_left * left_vel * m
        vr = self.sign_right * right_vel * m
        return 0.5 * (vl + vr), (vr - vl) / self.L

    # ---------------- odometry tu vi tri (vong) cua motor -------------- #
    def update_odometry(self, left_pos: float, right_pos: float) -> Tuple[float, float]:
        """Tra ve (quang duong d [m], goc quay dtheta [rad]) tu lan goi truoc."""
        if self._last is None:
            self._last = (left_pos, right_pos)
            return 0.0, 0.0
        m = self.meters_per_motor_turn
        dl = self.sign_left * (left_pos - self._last[0]) * m
        dr = self.sign_right * (right_pos - self._last[1]) * m
        self._last = (left_pos, right_pos)
        d = 0.5 * (dl + dr)
        dth = (dr - dl) / self.L
        self.x += d * math.cos(self.yaw + 0.5 * dth)
        self.y += d * math.sin(self.yaw + 0.5 * dth)
        self.yaw = wrap_angle(self.yaw + dth)
        return d, dth

    def reset_odometry(self):
        self.x = self.y = self.yaw = 0.0
        self._last = None
