import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    cfg = os.path.join(get_package_share_directory("robot_hardware"),
                       "config", "hub_driver.yaml")
    return LaunchDescription([
        DeclareLaunchArgument("use_sim_time", default_value="false"),
        Node(
            package="robot_hardware",
            executable="hub_driver_node",
            name="hub_driver",
            parameters=[cfg, {"use_sim_time": LaunchConfiguration("use_sim_time")}],
            output="screen",
        ),
        # Them rplidar_ros / robot_state_publisher o day khi ghep vao real.launch.py
    ])