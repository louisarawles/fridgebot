ROS 2 /cmd_vel to Arduino Uno motor control

Files:
  motor_control/motor_control.ino - Uno sketch
  cmd_vel_serial_bridge.py - standalone ROS 2 Twist-to-serial bridge

Connection:
  /joy -> gamepad_teleop -> /cmd_vel (geometry_msgs/msg/Twist)
       -> cmd_vel_serial_bridge.py -> USB at 9600 baud -> Arduino

Serial format: linear.x angular.z followed by newline, in m/s and rad/s.
Example: 0.0500 0.0000\n
The teleop publishes at 20 Hz. The bridge forwards each message without
repeating old commands. The Arduino stops driving after 500 ms without
a valid command. It starts stopped and stops on malformed commands.
Motor-driver faults latch until an Arduino reset.

Confirm these hardware settings before testing:
  WHEEL_RADIUS_M = 6 inches (preserved from original). If your wheels are
    6 inches in diameter, use 3.0 * 0.0254 instead.
  TRACK_WIDTH_M = 17.6875 inches, measured between wheel contact centerlines.
  MAX_WHEEL_RPM = 13.5 at the wheel output.
  M1 = left wheel, M2 = right wheel.
  LEFT_DIRECTION and RIGHT_DIRECTION = 1; use -1 for reversed wheel wiring.

This is open-loop PWM control, not measured wheel-speed control. RPM is a
calibration estimate; encoders and feedback are needed for accurate speeds.
With the original dimensions, maximum wheel speed is about 0.215 m/s.
Higher requests are scaled down together to preserve the left/right ratio.
Zero command means zero drive/coast, not active braking.

From the extracted folder, using the standalone Arduino CLI:
  ~/.local/bin/arduino-cli core update-index
  ~/.local/bin/arduino-cli core install arduino:avr
  ~/.local/bin/arduino-cli lib install DualVNH5019MotorShield
  ~/.local/bin/arduino-cli compile --fqbn arduino:avr:uno motor_control
  ~/.local/bin/arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:uno motor_control

Close screen, serial monitors, and any other bridge using this port first.
Opening the port normally resets an Uno; this bridge waits two seconds.
Use this bridge instead of another node that opens the same serial port.

In a terminal with ROS 2 and your workspace sourced:
  sudo apt install python3-serial
  python3 cmd_vel_serial_bridge.py --ros-args -p port:=/dev/ttyACM0 -p baud:=9600

Start your existing gamepad teleop and verify nonzero /cmd_vel first.
Fix its enable_button setting as discussed; the Arduino cannot correct zeros
already sent by teleop. Initial motor tests should have wheels off the ground.

Validation performed:
  Compiled for arduino:avr:uno with AVR core 1.8.8 and shield library 3.0.0.
  Flash: 5742 bytes. Static RAM: 276 bytes.
  Python bridge passed py_compile.
  Physical hardware and ROS runtime were not available for end-to-end testing.
