"""Launch the Gazebo robot together with saved-map navigation."""

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
        Launch the robot simulation, AMCL, Nav2 and optional RViz.

        Returns:
            launch_description: complete simulation and navigation launch description
    """
    simulation_share = get_package_share_directory("robot_simulation")
    navigation_share = get_package_share_directory("robot_navigation")

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
    navigation_launch = os.path.join(
        navigation_share,
        "launch",
        "navigation.launch.py",
    )

    """Launch Arguments"""
    world = LaunchConfiguration("world")
    use_sim_time = LaunchConfiguration("use_sim_time")
    use_rviz = LaunchConfiguration("use_rviz")
    map_file = LaunchConfiguration("map")
    params_file = LaunchConfiguration("params_file")

    """Simulation"""
    simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(simulation_launch),
        launch_arguments={
            "world": world,
            "use_sim_time": use_sim_time,
        }.items(),
    )

    """Navigation"""
    navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(navigation_launch),
        launch_arguments={
            "map": map_file,
            "params_file": params_file,
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
            "map",
            default_value=os.path.join(
                get_package_share_directory("robot_slam"),
                "maps",
                "lidar_world.yaml",
            ),
            description="Absolute path to the saved occupancy map YAML file.",
        ),
        DeclareLaunchArgument(
            "params_file",
            default_value=os.path.join(
                navigation_share,
                "config",
                "nav2_params.yaml",
            ),
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
        simulation,
        navigation,
    ])
