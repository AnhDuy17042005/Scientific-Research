"""Launch Nav2 localization and navigation on the saved LiDAR map."""

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
        Launch Nav2 with AMCL, the saved map and optional RViz.

        Returns:
            launch_description: Nav2 and RViz launch description
    """
    robot_navigation_share = get_package_share_directory("robot_navigation")
    robot_slam_share = get_package_share_directory("robot_slam")
    nav2_bringup_share = get_package_share_directory("nav2_bringup")

    default_map_file = os.path.join(
        robot_slam_share,
        "maps",
        "lidar_world.yaml",
    )
    default_params_file = os.path.join(
        robot_navigation_share,
        "config",
        "nav2_params.yaml",
    )
    default_rviz_config = os.path.join(
        nav2_bringup_share,
        "rviz",
        "nav2_default_view.rviz",
    )
    nav2_bringup_launch = os.path.join(
        nav2_bringup_share,
        "launch",
        "bringup_launch.py",
    )

    """Launch Arguments"""
    map_file = LaunchConfiguration("map")
    params_file = LaunchConfiguration("params_file")
    use_sim_time = LaunchConfiguration("use_sim_time")
    use_rviz = LaunchConfiguration("use_rviz")
    rviz_config = LaunchConfiguration("rviz_config")
    autostart = LaunchConfiguration("autostart")

    """Navigation"""
    navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(nav2_bringup_launch),
        launch_arguments={
            "map": map_file,
            "params_file": params_file,
            "use_sim_time": use_sim_time,
            "autostart": autostart,
            "slam": "False",
            "use_localization": "True",
        }.items(),
    )

    """Visualization"""
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
            "map",
            default_value=default_map_file,
            description="Absolute path to the saved occupancy map YAML file.",
        ),
        DeclareLaunchArgument(
            "params_file",
            default_value=default_params_file,
            description="Absolute path to the Nav2 parameter file.",
        ),
        DeclareLaunchArgument(
            "use_sim_time",
            default_value="true",
            description="Use the Gazebo simulation clock.",
        ),
        DeclareLaunchArgument(
            "use_rviz",
            default_value="true",
            description="Start RViz with the Nav2 configuration.",
        ),
        DeclareLaunchArgument(
            "rviz_config",
            default_value=default_rviz_config,
            description="Absolute path to the RViz configuration.",
        ),
        DeclareLaunchArgument(
            "autostart",
            default_value="true",
            description="Automatically activate the Nav2 lifecycle nodes.",
        ),
        navigation,
        rviz,
    ])
