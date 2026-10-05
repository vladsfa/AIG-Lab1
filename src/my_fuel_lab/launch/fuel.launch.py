import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    ExecuteProcess,
    IncludeLaunchDescription,
    RegisterEventHandler,
)
from launch.event_handlers import OnShutdown
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    pkg_my_fuel_lab = get_package_share_directory('my_fuel_lab')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    world_path = os.path.join(pkg_my_fuel_lab, 'worlds', 'fuel_world.sdf')
    bridge_config_path = os.path.join(pkg_my_fuel_lab, 'config', 'bridge.yaml')

    # Launch Gazebo Sim
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={
            'gz_args': f'-r {world_path}',
            'on_exit_shutdown': 'true',
        }.items(),
    )

    # Launch the bridge
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[{'config_file': bridge_config_path}],
        output='screen',
    )

    # Launch RViz2 (закриття вікна RViz спричинить завершення всього лаунчу)
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        output='screen',
        on_exit=Shutdown(),
    )

    # Примусове закриття дочірніх процесів Gazebo під час завершення лаунчу
    cleanup_gz = RegisterEventHandler(
        OnShutdown(
            on_shutdown=[
                ExecuteProcess(
                    cmd=['killall', '-9', 'ruby', 'gz'],
                    output='screen',
                )
            ]
        )
    )

    return LaunchDescription([
        gz_sim,
        bridge,
        rviz,
        cleanup_gz,
    ])