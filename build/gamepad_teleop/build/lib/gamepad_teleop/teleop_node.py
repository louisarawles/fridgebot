import math
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from geometry_msgs.msg import Twist

from gamepad_teleop.command_gate import CommandGate


class GamepadTeleop(Node):
    def __init__(self):
        super().__init__('gamepad_teleop')
        self.declare_parameter('linear_axis', 1)
        self.declare_parameter('angular_axis', 2)
        self.declare_parameter('linear_scale', 0.05)
        self.declare_parameter('angular_scale', 0.1)
        self.declare_parameter('angular_invert', True)
        self.declare_parameter('deadzone', 0.1)
        self.declare_parameter('enable_button', 9)
        self.declare_parameter('timeout_sec', 0.5)
        self.declare_parameter('publish_rate', 20.0)
        self.declare_parameter('neutral_hold_sec', 0.5)

        self.linear_scale = float(self.get_parameter('linear_scale').value)
        self.angular_scale = float(self.get_parameter('angular_scale').value)
        self.angular_invert = bool(self.get_parameter('angular_invert').value)
        rate = float(self.get_parameter('publish_rate').value)
        if not math.isfinite(rate) or rate <= 0:
            raise ValueError('publish_rate must be finite and positive')
        if not all(math.isfinite(value) and value >= 0
                   for value in (self.linear_scale, self.angular_scale)):
            raise ValueError('Speed scales must be finite and nonnegative')
        self.gate = CommandGate(
            linear_axis=int(self.get_parameter('linear_axis').value),
            angular_axis=int(self.get_parameter('angular_axis').value),
            enable_button=int(self.get_parameter('enable_button').value),
            deadzone=float(self.get_parameter('deadzone').value),
            timeout_sec=float(self.get_parameter('timeout_sec').value),
            neutral_hold_sec=float(self.get_parameter('neutral_hold_sec').value),
        )
        self.publisher = self.create_publisher(Twist, '/cmd_vel', 10)
        self.subscription = self.create_subscription(Joy, '/joy', self.joy_callback, 10)
        self.timer = self.create_timer(1.0 / rate, self.publish_command)
        self.reported_state = None
        self.report_state()

    def report_state(self):
        if self.gate.state == self.reported_state:
            return
        messages = {
            'waiting_neutral': 'Stopped: center both sticks and release the enable button.',
            'ready': 'Ready: press and hold the enable button with sticks centered, then move.',
            'active': 'Driving enabled; release the enable button to stop.',
        }
        self.get_logger().info(messages[self.gate.state])
        self.reported_state = self.gate.state

    def joy_callback(self, msg):
        self.gate.update(msg.axes, msg.buttons, time.monotonic())
        self.report_state()

    def publish_command(self):
        forward, turn = self.gate.command(time.monotonic())
        msg = Twist()
        msg.linear.x = forward * self.linear_scale
        msg.angular.z = turn * self.angular_scale * (-1.0 if self.angular_invert else 1.0)
        self.publisher.publish(msg)
        self.report_state()


def main(args=None):
    rclpy.init(args=args)
    node = GamepadTeleop()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            node.publisher.publish(Twist())
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
