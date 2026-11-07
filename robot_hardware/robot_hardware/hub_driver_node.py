import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, TransformStamped
from nav_msgs.msg import Odometry
from tf2_ros import TransformBroadcaster

from .bus import open_bus
from .kinematics import DiffDrive
from .odrive_can import ODriveAxis, decode_axis_error


class HubDriver(Node):
    def __init__(self):
        super().__init__("hub_driver")
        P = self.declare_parameter
        self.can_channel = P("can_channel", "can0").value
        left_id = P("left_id", 6).value
        right_id = P("right_id", 7).value
        radius = P("wheel_radius", 0.0825).value
        track = P("track_width", 0.40).value
        inv_l = P("invert_left", False).value
        inv_r = P("invert_right", True).value
        self.accel = P("accel", 2.0).value
        vel_limit = P("vel_limit", 3.0).value
        current = P("current_limit", 10.0).value
        self.max_v = P("max_linear", 0.5).value
        self.max_w = P("max_angular", 1.5).value
        self.timeout = P("cmd_timeout", 0.5).value
        rate = P("rate", 50.0).value
        self.odom_frame = P("odom_frame", "odom").value
        self.base_frame = P("base_frame", "base_link").value
        self.publish_tf = P("publish_tf", True).value

        self.dt = 1.0 / rate
        self.kin = DiffDrive(radius, track, 1.0, inv_l, inv_r)
        self.bus = open_bus(self.can_channel)
        self.left = ODriveAxis(self.bus, left_id, "L")
        self.right = ODriveAxis(self.bus, right_id, "R")

        if not (self.left.wait_for_data() and self.right.wait_for_data()):
            raise RuntimeError("Thieu du lieu tu ODrive, kiem tra CAN/node id")

        # ODrive may still publish the previous watchdog error in its heartbeat
        # just after Clear_Errors. Wait for a newer clean heartbeat before the
        # control timer can latch that stale error as a fault.
        for ax in (self.left, self.right):
            if not ax.clear_errors_and_wait():
                fb = ax.snapshot()
                raise RuntimeError(
                    "ODrive %s (node %d) van loi sau Clear_Errors: %s"
                    % (ax.name, ax.node_id, decode_axis_error(fb.axis_error)))
        for ax in (self.left, self.right):
            ax.start_velocity_control(vel_limit, current, clear_errors=False)

        self.out = [0.0, 0.0]
        self.cmd_v = self.cmd_w = 0.0
        self.last_cmd = self.get_clock().now()
        self.faulted = False

        self.create_subscription(Twist, "cmd_vel", self.on_cmd, 10)
        self.odom_pub = self.create_publisher(Odometry, "odom", 10)
        self.tf_br = TransformBroadcaster(self)
        self.create_timer(self.dt, self.loop)
        self.get_logger().info("hub_driver san sang")

    def on_cmd(self, msg: Twist):
        self.cmd_v = max(-self.max_v, min(self.max_v, msg.linear.x))
        self.cmd_w = max(-self.max_w, min(self.max_w, msg.angular.z))
        self.last_cmd = self.get_clock().now()

    def loop(self):
        now = self.get_clock().now()
        stale = (now - self.last_cmd).nanoseconds * 1e-9 > self.timeout
        v, w = (0.0, 0.0) if (stale or self.faulted) else (self.cmd_v, self.cmd_w)

        # v, w -> vong/s, co gioi han gia toc
        tl, tr = self.kin.twist_to_motor_turns(v, w)
        s = self.accel * self.dt
        self.out[0] += max(-s, min(s, tl - self.out[0]))
        self.out[1] += max(-s, min(s, tr - self.out[1]))
        self.left.set_input_vel(self.out[0])
        self.right.set_input_vel(self.out[1])

        a, b = self.left.snapshot(), self.right.snapshot()
        if a.axis_error or b.axis_error:
            self.faulted = True
            self.get_logger().error(
                "Loi trai=%s phai=%s" % (decode_axis_error(a.axis_error),
                                         decode_axis_error(b.axis_error)),
                throttle_duration_sec=1.0)
            self.out = [0.0, 0.0]
            return

        self.kin.update_odometry(a.pos, b.pos)
        self.publish_odom(now, v, w)

    def publish_odom(self, now, v, w):
        # DOI TEN thuoc tinh cho khop kinematics.py cua ban
        x, y, yaw = self.kin.x, self.kin.y, self.kin.yaw
        qz, qw = math.sin(yaw / 2), math.cos(yaw / 2)
        stamp = now.to_msg()

        od = Odometry()
        od.header.stamp = stamp
        od.header.frame_id = self.odom_frame
        od.child_frame_id = self.base_frame
        od.pose.pose.position.x = x
        od.pose.pose.position.y = y
        od.pose.pose.orientation.z = qz
        od.pose.pose.orientation.w = qw
        od.twist.twist.linear.x = v
        od.twist.twist.angular.z = w
        self.odom_pub.publish(od)

        if self.publish_tf:
            t = TransformStamped()
            t.header.stamp = stamp
            t.header.frame_id = self.odom_frame
            t.child_frame_id = self.base_frame
            t.transform.translation.x = x
            t.transform.translation.y = y
            t.transform.rotation.z = qz
            t.transform.rotation.w = qw
            self.tf_br.sendTransform(t)

    def stop(self):
        try:
            self.left.set_input_vel(0.0)
            self.right.set_input_vel(0.0)
        except Exception:
            pass


def main():
    rclpy.init()
    node = HubDriver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop()
        node.destroy_node()
        rclpy.shutdown()
