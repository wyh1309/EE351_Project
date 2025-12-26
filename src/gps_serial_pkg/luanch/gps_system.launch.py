from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch_ros.actions import Node
import os

def generate_launch_description():
    # 改成你实际的 web 目录路径
    web_root = os.path.expanduser('~/EE351_Project/web')

    return LaunchDescription([
        # 1️⃣ GPS 串口节点
        Node(
            package='gps_serial_pkg',
            executable='gps_serial_node',
            name='gps_serial_node',
            output='screen'
        ),

        # 2️⃣ WebSocket 转发节点
        Node(
            package='gps_serial_pkg',
            executable='gps_receiver_node',
            name='gps_receiver_node',
            output='screen'
        ),

        # 3️⃣ 启动网页服务器：python3 -m http.server 8080
        ExecuteProcess(
            cmd=['python3', '-m', 'http.server', '8080'],
            cwd=web_root,
            output='screen',
            shell=False
        ),
    ])
