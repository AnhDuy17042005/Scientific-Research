"""Launch a simple differential-drive robot with a 2D GPU LiDAR."""

"""Standard Library"""
import os

"""ROS 2 Launch"""
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


DESCRIPTION_PACKAGE = "robot_description"
SIMULATION_PACKAGE = "robot_simulation"
ROBOT_NAME = "simple_diff_robot"


def generate_launch_description():
    """
        Launch Gazebo, spawn the robot and bridge the LiDAR scan to ROS 2.

        Returns:
            launch_description: complete Gazebo and ROS 2 launch description
    """
    description_share = get_package_share_directory(DESCRIPTION_PACKAGE)
    simulation_share = get_package_share_directory(SIMULATION_PACKAGE)
    ros_gz_sim_share = get_package_share_directory("ros_gz_sim")

    robot_xacro_path = os.path.join(
        description_share,
        "urdf",
        "robot.xacro",
    )
    default_world_path = os.path.join(
        simulation_share,
        "worlds",
        "lidar_world.sdf",
    )
    bridge_config_path = os.path.join(
        simulation_share,
        "config",
        "gz_bridge.yaml",
    )
    gazebo_launch_path = os.path.join(
        ros_gz_sim_share,
        "launch",
        "gz_sim.launch.py",
    )

    """Launch Arguments"""
    world_argument = DeclareLaunchArgument(
        "world",
        default_value=default_world_path,
        description="Absolute path to the Gazebo world file.",
    )
    use_sim_time_argument = DeclareLaunchArgument(
        "use_sim_time",
        default_value="true",
        description="Use the Gazebo simulation clock.",
    )

    world = LaunchConfiguration("world")
    use_sim_time = LaunchConfiguration("use_sim_time")

    """Robot Description"""
    robot_description = ParameterValue(
        Command([
            "xacro ",
            robot_xacro_path,
        ]),
        value_type=str,
    )

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[{
            "robot_description": robot_description,
            "use_sim_time": use_sim_time,
        }],
    )

    """Gazebo"""
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(gazebo_launch_path),
        launch_arguments={
            "gz_args": ["-r -v 4 ", world],
        }.items(),
    )

    spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        name="spawn_robot",
        output="screen",
        arguments=[
            "-topic",
            "robot_description",
            "-name",
            ROBOT_NAME,
            "-x",
            "0.0",
            "-y",
            "0.0",
            "-z",
            "0.09",
        ],
    )

    """Gazebo-to-ROS Bridge"""
    gazebo_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="gazebo_bridge",
        output="screen",
        parameters=[{
            "config_file": bridge_config_path,
            "use_sim_time": use_sim_time,
        }],
    )

    return LaunchDescription([
        world_argument,
        use_sim_time_argument,
        robot_state_publisher,
        gazebo,
        spawn_robot,
        gazebo_bridge,
    ])
