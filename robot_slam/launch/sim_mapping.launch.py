"""Launch the Gazebo LiDAR simulation together with online 2D SLAM."""

"""Standard Library"""
import os

"""ROS 2 Launch"""
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    """
        Launch the robot simulation, SLAM Toolbox and optional RViz.

        Returns:
            launch_description: complete simulation and mapping launch description
    """
    simulation_share = get_package_share_directory("robot_simulation")
    robot_slam_share = get_package_share_directory("robot_slam")

    default_world = os.path.join(
        simulation_share,
        "worlds",
        "lidar_world.sdf",
    )
    simulation_launch = os.path.join(
        simulation_share,
        "launch",
        "lidar_sim.launch.py",
    )
    mapping_launch = os.path.join(
        robot_slam_share,
        "launch",
        "mapping.launch.py",
    )

    world = LaunchConfiguration("world")
    use_sim_time = LaunchConfiguration("use_sim_time")
    use_rviz = LaunchConfiguration("use_rviz")

    simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(simulation_launch),
        launch_arguments={
            "world": world,
            "use_sim_time": use_sim_time,
        }.items(),
    )

    mapping = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(mapping_launch),
        launch_arguments={
            "use_sim_time": use_sim_time,
            "use_rviz": use_rviz,
        }.items(),
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            "world",
            default_value=default_world,
            description="Absolute path to the Gazebo world file.",
        ),
        DeclareLaunchArgument(
            "use_sim_time",
            default_value="true",
            description="Use the Gazebo simulation clock.",
        ),
        DeclareLaunchArgument(
            "use_rviz",
            default_value="true",
            description="Start RViz with the mapping configuration.",
        ),
        simulation,
        mapping,
    ])
