import time

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Twist
from std_msgs.msg import Float32MultiArray

# linear regression values from testing
ANGULAR_FIT_SLOPE = 0.00396116
ANGULAR_FIT_INTERCEPT = 0.120253

LINEAR_FIT_SLOPE = 0.102558
LINEAR_FIT_INTERCEPT = 0.017093

class DistanceTracker(Node):

    def __init__(self):
        super().__init__('distance_tracker')

        self.subscription = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_callback,
            10
        )

        self.publisher = self.create_publisher(
            Float32MultiArray,
            '/estimates',
            10
        )

        # Cumulative estimates for the current movement
        self.distance = 0.0
        self.rotation = 0.0

        # Last commanded velocities
        self.v = 0.0
        self.w = 0.0

        # Timing
        self.last_update_time = time.monotonic()
        self.last_command_time = None
        self.command_timeout = 0.5

        # Zero-command detection
        self.zero_count = 0
        self.zero_threshold = 10

        # Tracking state
        self.command_active = False

        # Publish estimates at 100 Hz
        self.timer = self.create_timer(
            0.01,
            self.update_estimates
        )

        self.get_logger().info('Distance tracker started.')

    def integrate(self, now):
        """Accumulate motion using the previously commanded velocities."""
        dt = now - self.last_update_time

        if dt < 0:
            dt = 0.0

        if self.command_active:
            self.distance += abs(self.v) * dt
            self.rotation += abs(self.w) * dt

        self.last_update_time = now

    def cmd_callback(self, msg):
        now = time.monotonic()

        # First integrate using the velocity that was previously active.
        self.integrate(now)

        new_v = float(msg.linear.x)
        new_w = float(msg.angular.z)

        is_zero = (
            abs(new_v) < 1e-6
            and abs(new_w) < 1e-6
        )

        if is_zero:
            self.zero_count += 1

            # Freeze estimates after enough consecutive zero commands.
            if self.zero_count >= self.zero_threshold:
                self.v = 0.0
                self.w = 0.0
                self.command_active = False
                self.last_command_time = None

            self.publish_estimates()
            return

        # A nonzero command resets the zero counter.
        self.zero_count = 0

        # Begin a new measurement after the previous movement finishes.
        if not self.command_active:
            self.distance = 0.0
            self.rotation = 0.0
            self.command_active = True

            self.get_logger().info(
                'New movement detected. Estimates reset.'
            )

        # Store the new commanded velocities.
        self.v = new_v
        self.w = new_w
        self.last_command_time = now

        self.publish_estimates()

    def update_estimates(self):
        now = time.monotonic()

        # Integrate using the currently active velocities.
        self.integrate(now)

        # Freeze if command messages stop arriving.
        if (
            self.command_active
            and self.last_command_time is not None
            and now - self.last_command_time > self.command_timeout
        ):
            self.v = 0.0
            self.w = 0.0
            self.command_active = False
            self.last_command_time = None

            self.get_logger().info(
                'Command timeout. Estimates frozen.'
            )

        self.publish_estimates()

    def publish_estimates(self):
        msg = Float32MultiArray()
        corrected_rotation = max(
            0.0,
            (self.rotation - ANGULAR_FIT_INTERCEPT) / ANGULAR_FIT_SLOPE
        )
        corrected_distance = max (
            0.0,
            (self.distance - LINEAR_FIT_INTERCEPT) / LINEAR_FIT_SLOPE
        )
        
        msg.data = [float(corrected_distance), float(corrected_rotation)]
        self.publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = DistanceTracker()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
