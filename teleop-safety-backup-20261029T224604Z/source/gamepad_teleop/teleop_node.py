import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from geometry_msgs.msg import Twist


class GamepadTeleop(Node):
    def __init__(self):
        super().__init__('gamepad_teleop')

        self.declare_parameter('linear_axis', 1)
        self.declare_parameter('angular_axis', 2)
        self.declare_parameter('linear_scale', 0.1)
        self.declare_parameter('angular_scale', 0.1)
        self.declare_parameter('angular_invert', True)
        self.declare_parameter('deadzone', 0.1)
        self.declare_parameter('enable_button', -1)  # left shoulder on game_controller_node
        self.declare_parameter('timeout_sec', 0.5)
        self.declare_parameter('publish_rate', 20.0)

        self.linear_axis = int(self.get_parameter('linear_axis').value)
        self.angular_axis = int(self.get_parameter('angular_axis').value)
        self.linear_scale = float(self.get_parameter('linear_scale').value)
        self.angular_scale = float(self.get_parameter('angular_scale').value)
        self.angular_invert = bool(self.get_parameter('angular_invert').value)
        self.deadzone = float(self.get_parameter('deadzone').value)
        self.enable_button = int(self.get_parameter('enable_button').value)
        self.timeout_sec = float(self.get_parameter('timeout_sec').value)
        rate = float(self.get_parameter('publish_rate').value)
        if rate <= 0 or self.timeout_sec <= 0:
            raise ValueError('publish_rate and timeout_sec must be positive')

        self.publisher = self.create_publisher(Twist, '/cmd_vel', 10)
        self.subscription = self.create_subscription(Joy, '/joy', self.joy_callback, 10)
        self.target = Twist()
        self.last_joy_time = None
        self.timer = self.create_timer(1.0 / rate, self.publish_command)
        self.get_logger().info('Gamepad teleop: left Y -> linear.x, right X -> angular.z; hold left shoulder to enable')

    def filtered_axis(self, axes, index):
        if index < 0 or index >= len(axes):
            return 0.0
        value = max(-1.0, min(1.0, float(axes[index])))
        return 0.0 if abs(value) < self.deadzone else value

    def joy_callback(self, msg):
        self.last_joy_time = time.monotonic()
        self.target = Twist()
        enabled = (self.enable_button < 0 or
                   (self.enable_button < len(msg.buttons) and msg.buttons[self.enable_button] == 1))
        if not enabled:
            return
        forward = self.filtered_axis(msg.axes, self.linear_axis)
        turn = self.filtered_axis(msg.axes, self.angular_axis)
        self.target.linear.x = forward * self.linear_scale
        self.target.angular.z = turn * self.angular_scale * (-1.0 if self.angular_invert else 1.0)
        self.get_logger().info(
            f'enabled={enabled}, '
            f'axes=({self.linear_axis}, {self.angular_axis}), '
            f'filtered=({forward:.3f}, {turn:.3f}), '
            f'target=({self.target.linear.x:.3f}, {self.target.angular.z:.3f})'
        )

    def publish_command(self):
        fresh = (self.last_joy_time is not None and
                 time.monotonic() - self.last_joy_time <= self.timeout_sec)
        self.publisher.publish(self.target if fresh else Twist())


def main(args=None):
    rclpy.init(args=args)
    node = GamepadTeleop()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.publisher.publish(Twist())
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
