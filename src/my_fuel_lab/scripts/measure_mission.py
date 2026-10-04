#!/usr/bin/env python3
"""Measure asked vs got distance for the mission_demo.py route.

Runs the SAME segments as mission_demo.py while recording /odom,
then reports per-segment and total asked vs measured path length.

Usage:
    python3 src/my_fuel_lab/scripts/measure_mission.py [--wall-time | --sim-time]
Requires Gazebo + bridge running and unpaused.
"""
import argparse
import math
import time

import rclpy
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.parameter import Parameter
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry

# Must stay identical to mission_demo.py
SEGMENTS = [
    ("straight 1 (bottom segment)", 0.5, 0.0, 6.0),
    ("turn left 90deg", 0.0, 1.0, 1.57),
    ("straight 2", 0.5, 0.0, 4.0),
    ("loop", 0.5, 0.6, 10.0),
    ("straight 3 (final)", 0.5, 0.0, 4.0),
]


def quat_to_yaw(x, y, z, w):
    return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


class Recorder(Node):
    def __init__(self, use_sim_time: bool = True):
        super().__init__(
            'measure_mission',
            parameter_overrides=[Parameter('use_sim_time', Parameter.Type.BOOL, use_sim_time)],
        )
        self.xs = []
        self.ys = []
        self.yaw = 0.0
        self.has_odom = False
        self.create_subscription(Odometry, '/odom', self.cb, 10)

    def cb(self, msg: Odometry):
        self.xs.append(msg.pose.pose.position.x)
        self.ys.append(msg.pose.pose.position.y)
        q = msg.pose.pose.orientation
        self.yaw = quat_to_yaw(q.x, q.y, q.z, q.w)
        self.has_odom = True


def path_length(xs, ys, i0, i1):
    d = 0.0
    for i in range(max(i0 + 1, 1), min(i1, len(xs))):
        d += math.hypot(xs[i] - xs[i - 1], ys[i] - ys[i - 1])
    return d


def sim_now(node: Node):
    """Поточний час за годинником ROS (sim-time, якщо use_sim_time:=true)."""
    return node.get_clock().now()


def wait_for_sim_time(node: Node, timeout_wall_sec: float = 5.0) -> bool:
    """Чекає, поки /clock почне рухатись (nanoseconds > 0)."""
    t0 = time.time()
    while rclpy.ok() and time.time() - t0 < timeout_wall_sec:
        rclpy.spin_once(node, timeout_sec=0.1)
        if sim_now(node).nanoseconds > 0:
            return True
    return sim_now(node).nanoseconds > 0


def sleep_sim(node: Node, dur_sec: float):
    """Сон за SIM-часом: триває стільки, скільки потрібно фізиці Gazebo."""
    end = sim_now(node) + Duration(seconds=dur_sec)
    while rclpy.ok() and sim_now(node) < end:
        rclpy.spin_once(node, timeout_sec=0.05)
        # крихітна wall-пауза, щоб не палити CPU; тривалість міряємо лише по sim-time
        time.sleep(0.01)


def main():
    parser = argparse.ArgumentParser(
        description="Measure asked vs got distance for the mission_demo route."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--wall-time',
        action='store_true',
        help='Use system wall-clock time instead of Gazebo /clock'
    )
    group.add_argument(
        '--sim-time',
        action='store_true',
        help='Use Gazebo /clock sim time (default)'
    )
    args, ros_args = parser.parse_known_args()

    use_sim = not args.wall_time

    rclpy.init(args=ros_args)
    node = Recorder(use_sim_time=use_sim)
    pub = node.create_publisher(Twist, '/cmd_vel', 10)

    # wait for first /odom (wall-time, бо sim-time може ще стояти)
    t0 = time.time()
    while not node.has_odom and time.time() - t0 < 5.0:
        rclpy.spin_once(node, timeout_sec=0.1)
    if not node.has_odom:
        print('No /odom received. Is Gazebo running, unpaused, and bridged?')
        node.destroy_node()
        rclpy.shutdown()
        return

    mode_str = "sim time" if use_sim else "wall time"
    if use_sim:
        node.get_logger().info('Waiting for /clock (sim time)...')
        if not wait_for_sim_time(node, timeout_wall_sec=5.0):
            node.get_logger().warn(
                'No /clock received! Перевір bridge.yaml: має бути бридж '
                '/clock (gz.msgs.Clock -> rosgraph_msgs/msg/Clock). '
                'Продовжую, але тривалість буде мірятись некоректно.')
        else:
            node.get_logger().info(
                f'Sim time active: {sim_now(node).nanoseconds / 1e9:.2f}s')
    else:
        node.get_logger().info('Running in WALL-CLOCK mode (ignoring /clock)')

    sleep_sim(node, 1.0)

    results = []
    total_asked_dist = 0.0
    total_asked_angle = 0.0
    for desc, v, w, dur in SEGMENTS:
        i0 = len(node.xs)
        yaw0 = node.yaw
        msg = Twist()
        msg.linear.x = v
        msg.angular.z = w
        node.get_logger().info(f'{desc}: v={v} m/s, w={w} rad/s for {dur}s ({mode_str})')
        end = sim_now(node) + Duration(seconds=dur)
        while rclpy.ok() and sim_now(node) < end:
            pub.publish(msg)
            rclpy.spin_once(node, timeout_sec=0.05)
            time.sleep(0.02)  # лише щоб не спамити; межа циклу — sim-time
        pub.publish(Twist())
        sleep_sim(node, 0.5)
        for _ in range(5):
            rclpy.spin_once(node, timeout_sec=0.1)
        i1 = len(node.xs)
        got_dist = path_length(node.xs, node.ys, i0, i1)
        asked_dist = abs(v) * dur
        asked_angle = w * dur
        got_yaw = node.yaw - yaw0
        # normalize yaw delta to [-pi, pi]
        got_yaw = (got_yaw + math.pi) % (2 * math.pi) - math.pi
        results.append((desc, asked_dist, got_dist, asked_angle, got_yaw))
        total_asked_dist += asked_dist
        total_asked_angle += asked_angle

    pub.publish(Twist())
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()

    total_got = sum(r[2] for r in results)
    print()
    print(f'{"segment":30s} {"asked[m]":>9s} {"got[m]":>9s} {"diff[m]":>9s}')
    for desc, asked, got, _, _ in results:
        print(f'{desc:30s} {asked:9.2f} {got:9.2f} {abs(asked - got):9.2f}')
    print(f'{"TOTAL path length":30s} {total_asked_dist:9.2f} {total_got:9.2f} {abs(total_asked_dist - total_got):9.2f}')
    print(f'Total asked rotation: {total_asked_angle:.2f} rad ({math.degrees(total_asked_angle):.1f} deg)')
    print('Note: turn segment has asked_dist=0 (rotation on the spot); '
          'its small got[m] is wheel slip / drift during spin.')


if __name__ == '__main__':
    main()
