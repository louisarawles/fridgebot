#!/usr/bin/env python3
"""Timed, open-loop motion sequences published as ROS 2 Twist messages.

Input: 5m 30deg; 2m 90deg; 0m 90deg
Each step drives an arc, a straight line, or a spin in place.
Positive distance is forward; positive angle is counterclockwise.
Distances and angles are estimates: no odometry feedback is used.
The serial bridge converts Twist to the Arduino's text protocol.
"""
import math
import re
import time

import rclpy
from rclpy.signals import SignalHandlerOptions
from geometry_msgs.msg import Twist

# Match these settings to the Arduino sketch.
# If 6 inches is the wheel DIAMETER, use 3.0 * 0.0254 here and in the sketch.
WHEEL_RADIUS = 3.0 * 0.0254
TRACK_WIDTH = 17.75 * 0.0254
MAX_WHEEL_RPM = 13.5
SPEED_FRACTION = 0.5
WHEEL_SPEED_LIMIT = SPEED_FRACTION * MAX_WHEEL_RPM * 2.0 * math.pi / 60.0 * WHEEL_RADIUS
PUBLISH_PERIOD = 0.01  # 100 Hz; preserved from the calibration baseline.

LINEAR_CORRECTION = 0.1  # Preserve the baseline used for the measurements.
ANGULAR_CORRECTION = 0.227

ANGULAR_FIT_SLOPE = 0.9698
ANGULAR_FIT_INTERCEPT = 1.33

# Fit from 2026-10-29 measurements: measured = slope * input + intercept.
# Assumes measurements were collected with this uploaded baseline script.
# LINEAR_FIT_SLOPE = 0.9628571428571429
# LINEAR_FIT_INTERCEPT_M = 0.11357142857142843
LINEAR_FIT_MIN_M = 0.5
LINEAR_FIT_MAX_M = 4.0

LINEAR_FIT_SLOPE = 1.0687
LINEAR_FIT_INTERCEPT_M = -6.89

NUM = r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)'
STEP_RE = re.compile(rf'^({NUM})\s*m\s*({NUM})\s*deg$', re.IGNORECASE)


def send(pub, linear, angular):
    msg = Twist()
    msg.linear.x = float(linear)
    msg.angular.z = float(angular)
    pub.publish(msg)


def corrected_distance(requested_distance, requested_angle):
    """Inverse fit for tested forward straight moves; baseline for other moves."""
    command_distance = requested_distance
    # if (requested_angle == 0.0 and
    #        LINEAR_FIT_MIN_M <= requested_distance <= LINEAR_FIT_MAX_M):
    #    command_distance = (requested_distance - LINEAR_FIT_INTERCEPT_M) / LINEAR_FIT_SLOPE
    return command_distance * LINEAR_CORRECTION


def parse_line(line):
    segments = []
    for step in (s.strip() for s in line.split(';') if s.strip()):
        match = STEP_RE.fullmatch(step)
        if not match:
            raise ValueError(f"can't parse '{step}' (expected e.g. '5m 30deg')")
        requested_distance = float(match.group(1))
        requested_angle = math.radians(float(match.group(2)))
        if not (math.isfinite(requested_distance) and math.isfinite(requested_angle)):
            raise ValueError('distance and angle must be finite')
        distance = corrected_distance(requested_distance, requested_angle)
        angle = (requested_angle * ANGULAR_CORRECTION - ANGULAR_FIT_INTERCEPT) / ANGULAR_FIT_SLOP

        # Bound BOTH wheel speeds, including simultaneous forward + turning.
        left_distance = distance - angle * TRACK_WIDTH / 2.0
        right_distance = distance + angle * TRACK_WIDTH / 2.0
        duration = max(abs(left_distance), abs(right_distance)) / WHEEL_SPEED_LIMIT
        if not math.isfinite(duration):
            raise ValueError('motion is too large')
        if duration == 0.0:
            continue
        segments.append((distance / duration, angle / duration, duration))
    return segments


def stop(pub):
    # Repeat briefly so the bridge's periodic sender can observe the stop.
    for _ in range(5):
        send(pub, 0.0, 0.0)
        time.sleep(PUBLISH_PERIOD)


def run(pub, segments):
    try:
        for linear, angular, duration in segments:
            end = time.monotonic() + duration
            while rclpy.ok():
                remaining = end - time.monotonic()
                if remaining <= 0:
                    break
                send(pub, linear, angular)
                time.sleep(min(PUBLISH_PERIOD, remaining))
    finally:
        if rclpy.ok():
            stop(pub)


def main():
    # Let Ctrl+C reach the finally block before shutting down ROS.
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node = rclpy.create_node('cmd_vel_sequencer')
    pub = node.create_publisher(Twist, '/cmd_vel', 10)
    try:
        print('Waiting for a Twist subscriber on /cmd_vel...', flush=True)
        while rclpy.ok() and pub.get_subscription_count() == 0:
            rclpy.spin_once(node, timeout_sec=0.1)
        if not rclpy.ok():
            return
        print(f'Wheel speed limit: {WHEEL_SPEED_LIMIT:.3f} m/s (half speed)')
        print('Timed estimates only; no odometry feedback.')
        print('Linear regression correction active for forward straight moves of 0.5–4 m.')
        print('Enter: 5m 30deg; 2m 90deg; 0m 90deg  (Ctrl+C to stop and quit)')
        while rclpy.ok():
            try:
                segments = parse_line(input('> '))
            except ValueError as exc:
                print(f'Error: {exc}')
                continue
            if pub.get_subscription_count() == 0:
                print('No Twist subscriber; start the serial bridge and retry.')
                continue
            run(pub, segments)
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        try:
            if rclpy.ok():
                stop(pub)
        finally:
            node.destroy_node()
            if rclpy.ok():
                rclpy.shutdown()


if __name__ == '__main__':
    main()


