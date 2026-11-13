
import sys

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import Image
from rclpy.qos import qos_profile_sensor_data
from cv_bridge import CvBridge

from geometry_msgs.msg import Twist
from std_msgs.msg import Float32MultiArray

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout,
    QLabel
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap


class WheelControlGUI(QWidget):
    def __init__(self, node):
        super().__init__()
        self.node = node

        self.bridge = CvBridge()

        # subscriber for the estimated distance and rotation
        self.estimate_subscriber = node.create_subscription(
            Float32MultiArray,
            '/estimates',
            self.estimates_callback,
            10
        )

        # subscriber for camera image
        self.image_subscriber = node.create_subscription(
            Image, 
            '/sensor_msgs/msg/CompressedImage', 
            self.image_callback, 
            qos_profile_sensor_data
        )

        self.setWindowTitle("Estimated Rotation + Distance Traveled with Camera Feed")
        self.resize(750, 650)

        layout = QVBoxLayout()

        # camera feed + display
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(640, 360)

        layout.addWidget(self.image_label)

        # speed information from cmd_vel
        self.rotation_label = QLabel("Estimated Rotation: 0.0 degrees")
        self.rotation_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.rotation_label)

        # information from distance tracker
        self.distance_label = QLabel("Estimated Distance Traveled: 0.0 m")
        self.distance_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.distance_label)

        self.setLayout(layout)


        # callback processing
        self.ros_timer = QTimer(self)
        self.ros_timer.timeout.connect(self.spin_ros)
        self.ros_timer.start(5)
    
    def spin_ros(self):
        for _ in range(20):
            rclpy.spin_once(self.node, timeout_sec=0)

    def estimates_callback(self, msg):
        if len(msg.data) >= 2:
            distance = msg.data[0]
            rotation = msg.data[1]
            self.distance_label.setText(
                f"Estimated Distance: {distance:.2f} m"
            )
            self.rotation_label.setText(
                f"Estimated Rotation: {rotation:.2f} degrees"
            )
        else:
            self.distance_label.setText(
                "Estimated Distance: 0.0 m"
            )
            self.rotation_label.setText(
                f"Estimated Rotation: 0.0 degrees"
            )
    def image_callback(self, msg):

        try:
            # ROS Image -> OpenCV RGB array
            frame = self.bridge.imgmsg_to_cv2(
                msg,
                desired_encoding='rgb8'
            )

            height, width, channels = frame.shape

            bytes_per_line = channels * width

            q_image = QImage(
                frame.data,
                width,
                height,
                bytes_per_line,
                QImage.Format_RGB888
            ).copy()

            pixmap = QPixmap.fromImage(q_image)

            pixmap = pixmap.scaled(
                self.image_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            self.image_label.setPixmap(pixmap)

        except Exception as e:
            self.node.get_logger().error(
                f"Camera error: {e}"
            )

    def closeEvent(self, event):
        self.ros_timer.stop()
        event.accept()


def main():
    rclpy.init()
    node = Node("wheel_control_gui")

    app = QApplication(sys.argv)
    gui = WheelControlGUI(node)
    gui.show()

    try:
        app.exec_()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
