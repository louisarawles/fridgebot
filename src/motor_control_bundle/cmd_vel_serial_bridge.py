#!/usr/bin/env python3
"""Forward ROS 2 Twist messages as newline-delimited velocity pairs."""
import math
import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
import serial


class CmdVelSerialBridge(Node):
    def __init__(self):
        super().__init__('cmd_vel_serial_bridge')
        self.declare_parameter('port', '/dev/ttyACM0')
        self.declare_parameter('baud', 9600)
        self.ser = serial.Serial(
            self.get_parameter('port').value,
            int(self.get_parameter('baud').value),
            timeout=0, write_timeout=0.2,
        )
        try:
            # Opening an Uno serial port normally resets the board.
            time.sleep(2.0)
            self.ser.reset_input_buffer()
            self.send(0.0, 0.0)
            self.subscription = self.create_subscription(
                Twist, '/cmd_vel', self.on_cmd_vel, qos_profile_sensor_data)
        except Exception:
            self.ser.close()
            raise
        self.get_logger().info(
            f'Forwarding /cmd_vel to {self.ser.port} at {self.ser.baudrate} baud')

    def send(self, v, w):
        payload = f'{v:.4f} {w:.4f}\n'.encode('ascii')
        # Reject values too large for the Arduino frame buffer.
        if len(payload) > 63:
            payload = b'0.0000 0.0000\n'
        if self.ser.write(payload) != len(payload):
            raise serial.SerialException('Incomplete serial command write')

    def on_cmd_vel(self, msg):
        v, w = msg.linear.x, msg.angular.z
        if not (math.isfinite(v) and math.isfinite(w)):
            self.get_logger().error('Invalid velocity; sending zero')
            v, w = 0.0, 0.0
        self.send(v, w)
        # No replay timer: if /cmd_vel stops, the Arduino times out in 500 ms.

    def close(self):
        try:
            self.send(0.0, 0.0)
        except serial.SerialException:
            pass  # Arduino timeout covers loss of the serial connection.
        finally:
            self.ser.close()


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = CmdVelSerialBridge()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.close()
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
