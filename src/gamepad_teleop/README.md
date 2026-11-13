# gamepad_teleop (ROS 2 Jazzy)

Gamepad `game_controller_node` -> `/joy` (`sensor_msgs/msg/Joy`) -> custom `gamepad_teleop` -> `/cmd_vel` (`geometry_msgs/msg/Twist`).

- Left joystick up/down: forward/backward (`linear.x`)
- Right joystick left/right: robot turn left/right (`angular.z`)
- Hold **left shoulder** to move (button index 9). Releasing stops the robot.
- Default maximum speeds: 0.3 m/s forward/backward, 0.8 rad/s rotation.
- Deadzone 0.1, gamepad timeout 0.5 s; publishes at 20 Hz, including zeros when disabled or disconnected.

## Install and build

```bash
sudo apt update
sudo apt install ros-jazzy-joy
mkdir -p ~/robotics/src
cp -r gamepad_teleop ~/robotics/src/
cd ~/robotics
source /opt/ros/jazzy/setup.bash
colcon build --packages-select gamepad_teleop --symlink-install
source install/setup.bash
```

## Run

```bash
ros2 launch gamepad_teleop gamepad_teleop.launch.py
```

In another sourced terminal:

```bash
ros2 topic echo /joy
ros2 topic echo /cmd_vel
```

First test with wheels off the floor / robot physically immobilized. To change axis indices, direction, speeds, enable button or timeout, edit `config/teleop.yaml` and rebuild/relaunch. The normalized axis indices assume `game_controller_node`. If your controller doesn't behave as expected inspect `/joy` and change the indices/sign.
