from setuptools import find_packages, setup
from glob import glob
import os

package_name = 'gamepad_teleop'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ROS 2 Developer',
    maintainer_email='developer@example.com',
    description='Gamepad left/right joystick teleoperation to /cmd_vel',
    license='Apache-2.0',
    entry_points={'console_scripts': [
        'teleop_node = gamepad_teleop.teleop_node:main',
    ]},
)
