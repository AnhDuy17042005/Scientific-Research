"""Launch SLAM Toolbox and optionally RViz for online 2D mapping."""

"""Standard Library"""
import os

"""ROS 2 Launch"""
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    """
        Launch SLAM Toolbox with the project configuration.

        Returns:
            launch_description: SLAM Toolbox and optional RViz launch description
    """
    robot_slam_share = get_package_share_directory("robot_slam")
    slam_toolbox_share = get_package_share_directory("slam_toolbox")

    default_slam_params_file = os.path.join(
        robot_slam_share,
        "config",
        "slam_toolbox.yaml",
    )
    default_rviz_config = os.path.join(
        robot_slam_share,
        "rviz",
        "mapping.rviz",
    )
    slam_toolbox_launch = os.path.join(
        slam_toolbox_share,
        "launch",
        "online_async_launch.py",
    )

    use_sim_time = LaunchConfiguration("use_sim_time")
    slam_params_file = LaunchConfiguration("slam_params_file")
    use_rviz = LaunchConfiguration("use_rviz")
    rviz_config = LaunchConfiguration("rviz_config")

    slam_toolbox = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(slam_toolbox_launch),
        launch_arguments={
            "use_sim_time": use_sim_time,
            "slam_params_file": slam_params_file,
        }.items(),
    )

    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz",
        output="screen",
        arguments=["-d", rviz_config],
        parameters=[{
            "use_sim_time": use_sim_time,
        }],
        condition=IfCondition(use_rviz),
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            "use_sim_time",
            default_value="true",
            description="Use the Gazebo simulation clock.",
        ),
        DeclareLaunchArgument(
            "slam_params_file",
            default_value=default_slam_params_file,
            description="Absolute path to the SLAM Toolbox parameter file.",
        ),
        DeclareLaunchArgument(
            "use_rviz",
            default_value="true",
            description="Start RViz with the mapping configuration.",
        ),
        DeclareLaunchArgument(
            "rviz_config",
            default_value=default_rviz_config,
            description="Absolute path to the RViz mapping configuration.",
        ),
        slam_toolbox,
        rviz,
    ])
