from launch import LaunchDescription, LaunchContext
from launch.actions import ExecuteProcess, DeclareLaunchArgument, OpaqueFunction, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, Command, FindExecutable
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare

from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
import os

def launch_setup(
    context: LaunchContext, *args, **kwargs
) :

    gz_verbose = LaunchConfiguration("gz_verbose")
    gz_headless = LaunchConfiguration("gz_headless")
    robot_name = LaunchConfiguration("robot_name")
    gz_verbose_bool = context.perform_substitution(gz_verbose).lower() == "true"
    gz_headless_bool = context.perform_substitution(gz_headless).lower() == "true"
    robot_name_str = context.perform_substitution(robot_name).lower()
    # Set the package path for Gazebo
    xacro_name = ""
    if robot_name_str == "so-101":
        xacro_name = 'so101_new_calib.urdf.xacro'
    elif robot_name_str == "lekiwi":
        xacro_name = 'le_kiwi.urdf.xacro'
    else:
        print("unknown robot")
    robot_description = ParameterValue(Command([FindExecutable(name='xacro'),' ', PathJoinSubstitution([FindPackageShare('so_100_arm'), 'urdf',xacro_name])]), value_type=str
    )
    gz_gui_config_path_str = context.perform_substitution(
        PathJoinSubstitution(
            [
                FindPackageShare("so_100_arm"),
                "config",
                "gz_gui.config",
            ]
        )
    )
    gz_world_path = PathJoinSubstitution(
                [
                    FindPackageShare("so_100_arm"),
                    "config",
                    "empty.sdf",
                ]
            )
    gz_world_path_str = context.perform_substitution(gz_world_path)
    gazebo_empty_world = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [
                    FindPackageShare("ros_gz_sim"),
                    "launch",
                    "gz_sim.launch.py",
                ]
            )
        ),
        launch_arguments={
            "gz_args": gz_world_path_str
            + " -r"
            + f" {'-s' if gz_headless_bool else ''}"
            + f" {'-v 3' if gz_verbose_bool else ''}"
            + f" --gui-config {gz_gui_config_path_str}"
        }.items(),
    )

    ros_gz_bridge_node = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        parameters=[
            {
                "expand_gz_topic_names": True,
                "use_sim_time": True,
                "config_file": PathJoinSubstitution(
                    [
                        FindPackageShare("so_100_arm"),
                        "config",
                        "gz_bridge.yaml",
                    ]
                ),
            }
        ],
        output="screen",
    )
    #robot_description = Command([FindExecutable(name='xacro'),' ', pkg_share + '/config/so_100_arm.urdf.xacro'])
                                 #PathJoinSubstitution([FindPackageShare('so_100_arm'), 'config','so_100_arm.urdf.xacro'])])
    robot_state_publisher_node = Node(
                package='robot_state_publisher',
                executable='robot_state_publisher',
                output='screen',
                parameters=[{'robot_description': robot_description}]
            )
    """
    robot_spawn_node = Node(package='gazebo_ros',executable='spawn_entity.py',
                            arguments=['-topic', 'robot_description','-entity', 'robot'],
                            output='screen')
    """
    robot_spawn_node = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=["-topic", "/robot_description"],
        parameters=[{"use_sim_time": True}],
        output="screen",
    )

     # Define the controller spawner nodes
    joint_state_broadcaster_spawner = ExecuteProcess(
        cmd=['ros2', 'control', 'load_controller', '--set-state', 'active',
            'joint_state_broadcaster'],
        output='screen'
    )

    joint_trajectory_controller_spawner = ExecuteProcess(
        cmd=['ros2', 'control', 'load_controller', '--set-state', 'active',
            'so_100_arm_controller'],
        output='screen'
    )

    # Add gripper controller spawner
    gripper_controller_spawner = ExecuteProcess(
        cmd=['ros2', 'control', 'load_controller', '--set-state', 'active',
            'so_100_arm_gripper_controller'],
        output='screen'
    )

    return [
        #gazebo_launch,
        gazebo_empty_world,
        ros_gz_bridge_node,
        robot_state_publisher_node,
        robot_spawn_node,
        # Spawn joint_state_broadcaster after robot spawns
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=robot_spawn_node,
                on_exit=[joint_state_broadcaster_spawner,joint_trajectory_controller_spawner,gripper_controller_spawner],#spawn_default_controllers
            )
        ),
        
    ]

def generate_launch_description():
    declared_arguments = [
        DeclareLaunchArgument(
            "gz_verbose",
            default_value="false",
            description="Whether to set verbosity level of Gazebo to 3.",
            choices=["true", "false"],
        ),
        DeclareLaunchArgument(
            "gz_headless",
            default_value="false",
            description="Whether to launch Gazebo in headless mode (no GUI is launched, only physics server).",
            choices=["true", "false"],
        ),
        DeclareLaunchArgument(
            "robot_name",
            default_value="so-101",
            description="Which robot to use.",
            choices=["so-101", "lekiwi"],
        ),
        ]
    return LaunchDescription(
        declared_arguments + [OpaqueFunction(function=launch_setup)]
    )