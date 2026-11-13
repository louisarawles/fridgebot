from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    config = str(Path(get_package_share_directory('gamepad_teleop')) / 'config' / 'teleop.yaml')
    return LaunchDescription([
        Node(
            package='joy',
            executable='game_controller_node',
            name='game_controller',
            output='screen',
            parameters=[{'deadzone': 0.05, 'autorepeat_rate': 20.0}],
            remappings=[('joy', '/joy')],
        ),
        Node(
            package='gamepad_teleop',
            executable='teleop_node',
            name='gamepad_teleop',
            output='screen',
            parameters=[config],
        ),
    ])
