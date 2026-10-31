"""Show a virtual robot following real LD06 odometry while RTAB-Map maps it."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def validate_mode(context, *args, **kwargs):
    if (
        LaunchConfiguration("localization").perform(context) == "true"
        and LaunchConfiguration("reset_map").perform(context) == "true"
    ):
        raise RuntimeError(
            "Localization needs the saved database: use reset_map:=false localization:=true"
        )
    return []


def generate_launch_description():
    description_share = get_package_share_directory("robot_description")
    simulation_share = get_package_share_directory("robot_simulation")
    slam_share = get_package_share_directory("robot_slam")
    gazebo_share = get_package_share_directory("ros_gz_sim")
    rtabmap_share = get_package_share_directory("rtabmap_launch")

    world = os.path.join(
        simulation_share, "worlds", "real_scan_visualization.sdf"
    )
    xacro_file = os.path.join(description_share, "urdf", "robot.xacro")
    rviz_file = os.path.join(slam_share, "rviz", "mapping.rviz")
    gazebo_launch = os.path.join(gazebo_share, "launch", "gz_sim.launch.py")
    rtabmap_launch = os.path.join(rtabmap_share, "launch", "rtabmap.launch.py")

    lidar_mount_height = LaunchConfiguration("lidar_mount_height")
    robot_description = ParameterValue(
        Command([
            "xacro ",
            xacro_file,
            " gazebo_plugins:=false lidar_mount_height:=",
            lidar_mount_height,
        ]),
        value_type=str,
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            "database_path",
            default_value=os.path.expanduser("~/.ros/rtabmap_real_ld06.db"),
            description="RTAB-Map database for the real LD06 mapping session.",
        ),
        DeclareLaunchArgument(
            "reset_map",
            default_value="true",
            choices=["true", "false"],
            description="Delete the previous RTAB-Map database on startup.",
        ),
        DeclareLaunchArgument(
            "localization",
            default_value="false",
            choices=["true", "false"],
            description="Localize real scans against an existing RTAB-Map database.",
        ),
        DeclareLaunchArgument(
            "lidar_mount_height",
            default_value="0.18",
            description="Real base_link -> base_laser height in metres.",
        ),
        OpaqueFunction(function=validate_mode),
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            parameters=[{"robot_description": robot_description, "use_sim_time": False}],
            output="screen",
        ),
        Node(
            package="joint_state_publisher",
            executable="joint_state_publisher",
            parameters=[{"use_sim_time": False}],
            output="screen",
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(gazebo_launch),
            launch_arguments={"gz_args": ["-r -v 3 ", world]}.items(),
        ),
        Node(
            package="ros_gz_sim",
            executable="create",
            name="spawn_visual_robot",
            arguments=[
                "-topic", "robot_description",
                "-name", "simple_diff_robot",
                "-x", "0", "-y", "0", "-z", "0.09",
            ],
            output="screen",
        ),
        Node(
            package="ros_gz_bridge",
            executable="parameter_bridge",
            name="gazebo_set_pose_bridge",
            arguments=[
                "/world/real_scan_visualization/set_pose@ros_gz_interfaces/srv/SetEntityPose"
            ],
            output="screen",
        ),
        Node(
            package="robot_slam",
            executable="follow_real_odom.py",
            output="screen",
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(rtabmap_launch),
            launch_arguments={
                "depth": "false",
                "subscribe_rgb": "false",
                "visual_odometry": "false",
                "icp_odometry": "true",
                "subscribe_scan": "true",
                "scan_topic": "/scan",
                "frame_id": "base_link",
                "odom_topic": "/odom",
                "vo_frame_id": "odom",
                "odom_frame_id": "odom",
                "map_topic": "/map",
                "database_path": LaunchConfiguration("database_path"),
                "localization": LaunchConfiguration("localization"),
                "args": PythonExpression([
                    "'-d' if '", LaunchConfiguration("reset_map"), "' == 'true' else ''"
                ]),
                "qos": "2",
                "use_sim_time": "false",
                "rtabmap_viz": "false",
                "rviz": "true",
                "rviz_cfg": rviz_file,
            }.items(),
        ),
    ])
