#!/usr/bin/env python3
"""Record /odom (x, y) and save X-Y path plot to src/my_fuel_lab/path.png.

Usage:
    python3 src/my_fuel_lab/scripts/plot_path.py
    # drive robot (teleop or ros2 topic pub), then Ctrl+C to save plot
"""
import math
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry


class PathRecorder(Node):
    def __init__(self):
        super().__init__('path_recorder')
        self.xs = []
        self.ys = []
        self.create_subscription(Odometry, '/odom', self.cb, 10)
        self.get_logger().info('Recording /odom... Ctrl+C to save path.png')

    def cb(self, msg: Odometry):
        self.xs.append(msg.pose.pose.position.x)
        self.ys.append(msg.pose.pose.position.y)


def main():
    rclpy.init()
    node = PathRecorder()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        xs, ys = node.xs, node.ys
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

    if len(xs) < 2:
        print(f'Only {len(xs)} points recorded, nothing to plot.')
        return

    dist = sum(math.hypot(xs[i] - xs[i-1], ys[i] - ys[i-1]) for i in range(1, len(xs)))
    plt.figure()
    plt.plot(xs, ys, '-o', markersize=2)
    plt.plot(xs[0], ys[0], 'go', label='start')
    plt.plot(xs[-1], ys[-1], 'ro', label='end')
    plt.xlabel('x [m]')
    plt.ylabel('y [m]')
    plt.title(f'Husky path from /odom ({len(xs)} pts, ~{dist:.2f} m)')
    plt.axis('equal')
    plt.grid(True)
    plt.legend()
    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'path.png')
    plt.savefig(out_path, dpi=150)
    print(f'Saved {out_path}: {len(xs)} points, path length ~{dist:.2f} m')


if __name__ == '__main__':
    main()
