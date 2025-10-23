from launch import LaunchDescription, LaunchContext
from launch.actions import ExecuteProcess, DeclareLaunchArgument, OpaqueFunction, RegisterEventHandler, TimerAction
from launch.event_handlers import OnProcessExit
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, Command, FindExecutable
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare
from controller_manager_msgs.srv import SwitchController
from controller_manager.launch_utils import (
    generate_controllers_spawner_launch_description,  # noqa: I001
)
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
import os
"""
def get_robot_description(context, *args, **kwargs):
    dof = LaunchConfiguration('dof').perform(context)
    pkg_share = FindPackageShare('so_100_arm').find('so_100_arm')
    urdf_path = os.path.join(pkg_share, 'urdf', f'so_100_arm_{dof}dof.urdf')
    controller_path = os.path.join(pkg_share, 'config', f'controllers_{dof}dof.yaml')
    
    with open(urdf_path, 'r') as file:
        urdf_content = file.read()
        # Convert package:// to model:// for Gazebo
        replace_str = f'package://so_100_arm/models/so_100_arm_{dof}dof/meshes'
        with_str = f'model://so_100_arm_{dof}dof/meshes'
        gazebo_urdf_content = urdf_content.replace(replace_str, with_str)
        with open("test.txt",'w') as f:
            f.write(gazebo_urdf_content)
        return {
            'robot_description': ParameterValue(urdf_content, value_type=str),
            'gazebo_description': ParameterValue(gazebo_urdf_content, value_type=str),
            'controller_path': controller_path
        }
"""
def launch_setup(
    context: LaunchContext, *args, **kwargs
) :

    pkg_share = FindPackageShare('so_100_arm').find('so_100_arm')
    model_path = os.path.join(os.path.dirname(os.path.dirname(pkg_share)), 'models')
    gz_verbose = LaunchConfiguration("gz_verbose")
    gz_headless = LaunchConfiguration("gz_headless")

    gz_verbose_bool = context.perform_substitution(gz_verbose).lower() == "true"
    gz_headless_bool = context.perform_substitution(gz_headless).lower() == "true"
    # Set the package path for Gazebo
    """
    if 'GZ_SIM_RESOURCE_PATH' in os.environ:
        os.environ['GZ_SIM_RESOURCE_PATH'] += f":{model_path}"
    else:
        os.environ['GZ_SIM_RESOURCE_PATH'] = model_path
    """
    """
    descriptions = get_robot_description(context)
    
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        name='spawn_model',
        arguments=[
            '-string', descriptions['gazebo_description'].value,
            '-name', 'so_100_arm',
            '-allow_renaming', 'true',
            '-x', '0',
            '-y', '0',
            '-z', '0'
        ],
        output='screen'
    )
    """
    #gazebo_launch = IncludeLaunchDescription(PythonLaunchDescriptionSource(
    #    [PathJoinSubstitution([FindPackageShare('gazebo_ros'),'launch','gazebo.launch.py'])]))
    urdf_path = os.path.join(pkg_share, 'urdf', 'so101_new_calib.urdf')
    with open(urdf_path, 'r') as file:
        urdf_content = file.read()
    robot_description = ParameterValue(Command([FindExecutable(name='xacro'),' ', PathJoinSubstitution([FindPackageShare('so_100_arm'), 'urdf','so101_new_calib.urdf.xacro'])]), value_type=str
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

    controllers = ["joint_state_broadcaster","joint_trajectory_controller", "gripper_controller"]
    spawn_default_controllers = generate_controllers_spawner_launch_description(
        controllers
    )
    """
    RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=robot_spawn_node,
                on_exit=[TimerAction(period=5.0, actions=[joint_state_broadcaster_spawner])]
            )
        ),

        # Spawn joint_trajectory_controller after joint_state_broadcaster
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=joint_state_broadcaster_spawner,
                on_exit=[joint_trajectory_controller_spawner]
            )
        ),

        # Add gripper controller after joint_trajectory_controller
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=joint_trajectory_controller_spawner,
                on_exit=[gripper_controller_spawner]
            )
        )
    """

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
        ]
    return LaunchDescription(
        declared_arguments + [OpaqueFunction(function=launch_setup)]
    )