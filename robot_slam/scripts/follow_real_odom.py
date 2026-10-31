#!/usr/bin/env python3
"""Mirror scan-derived odometry into a Gazebo model used for visualization."""

import copy

import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from ros_gz_interfaces.msg import Entity
from ros_gz_interfaces.srv import SetEntityPose


class FollowRealOdom(Node):
    def __init__(self):
        super().__init__("follow_real_odom")
        self.declare_parameter("entity_name", "simple_diff_robot")
        self.declare_parameter(
            "service_name", "/world/real_scan_visualization/set_pose"
        )
        self.declare_parameter("height_offset", 0.09)
        self.entity_name = self.get_parameter("entity_name").value
        service_name = self.get_parameter("service_name").value
        self.height_offset = self.get_parameter("height_offset").value
        self.client = self.create_client(SetEntityPose, service_name)
        self.latest_pose = None
        self.pending = None
        self.reported_success = False
        self.create_subscription(Odometry, "/odom", self.on_odom, 10)
        self.create_timer(0.1, self.update_model)

    def on_odom(self, msg):
        if msg.header.frame_id != "odom" or msg.child_frame_id != "base_link":
            self.get_logger().warn(
                "Expected odom -> base_link in /odom; ignoring incompatible message",
                throttle_duration_sec=10.0,
            )
            return
        self.latest_pose = copy.deepcopy(msg.pose.pose)

    def update_model(self):
        if self.latest_pose is None or self.pending is not None:
            return
        if not self.client.service_is_ready():
            return
        request = SetEntityPose.Request()
        request.entity.name = self.entity_name
        request.entity.type = Entity.MODEL
        request.pose = self.latest_pose
        request.pose.position.z += self.height_offset
        self.pending = self.client.call_async(request)
        self.pending.add_done_callback(self.on_pose_result)

    def on_pose_result(self, future):
        self.pending = None
        try:
            success = future.result().success
        except Exception as exc:  # Gazebo may disappear while the node is running.
            self.get_logger().warn(f"Gazebo set_pose failed: {exc}")
            return
        if success and not self.reported_success:
            self.get_logger().info("Gazebo robot now follows /odom")
            self.reported_success = True
        elif not success and self.reported_success:
            self.get_logger().warn("Gazebo rejected a set_pose request")
            self.reported_success = False


def main():
    rclpy.init()
    node = FollowRealOdom()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
