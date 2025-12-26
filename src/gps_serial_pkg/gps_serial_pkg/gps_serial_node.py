#!/usr/bin/env python3
import os
import serial
import time
import subprocess

import rclpy
from rclpy.node import Node
from gps_interfaces.msg import GpsSimple


PORT = "/dev/ttyUSB0"
BAUD = 115200

FRAME_HEADER = b'\xAA\x55'


def build_packet(msg_type: int, payload: bytes) -> bytes:
    length = 1 + len(payload)
    body = bytes([length, msg_type]) + payload
    checksum = sum(body) & 0xFF
    return FRAME_HEADER + body + bytes([checksum])


class GpsSerialNode(Node):
    def __init__(self):
        super().__init__("gps_serial_node")

        # 串口
        self.get_logger().info(f"Opening serial: {PORT} @ {BAUD}")
        self.ser = serial.Serial(PORT, BAUD, timeout=0.01)

        # 接收缓冲
        self.rx_buffer = bytearray()

        # 发布 GPS 的话题
        self.pub_gps = self.create_publisher(GpsSimple, "gps/simple", 10)

        # 音频文件路径（直接指向工作空间 src 目录）
        project_root = os.path.expanduser("~/EE351_Project")
        sound_dir = os.path.join(
            project_root, "src", "gps_serial_pkg", "gps_serial_pkg", "sounds"
        )

        self.red_audio = os.path.join(sound_dir, "red_box.wav")
        self.yellow_audio = os.path.join(sound_dir, "yellow_box.wav")

        self.get_logger().info(f"RED audio path: {self.red_audio}")
        self.get_logger().info(f"YELLOW audio path: {self.yellow_audio}")

        # 防止一直刷同一个音频：加个冷却时间
        self.last_red_play = 0.0
        self.last_yellow_play = 0.0
        self.play_cooldown = 1.0  # 秒

        # 定时器：轮询串口
        self.timer = self.create_timer(0.005, self.loop_once)

    # ===== 音频播放函数 =====
    def play_sound(self, path: str, label: str):
        if not os.path.exists(path):
            self.get_logger().warn(f"Audio file not found: {path}")
            return

        try:
            # 使用 aplay 播放 wav，非阻塞
            self.get_logger().info(
                f"Playing {label} audio with aplay: {os.path.basename(path)}"
            )
            subprocess.Popen(
                ["aplay", path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except FileNotFoundError:
            self.get_logger().error(
                "Command 'aplay' not found. Please install it: sudo apt install alsa-utils"
            )
        except Exception as e:
            self.get_logger().error(f"Failed to play {label} audio: {e}")

    def handle_gps_payload(self, payload: str):
        try:
            lat_str, lon_str, sats_str = payload.split(',')
            lat = float(lat_str)
            lon = float(lon_str)
            sats = int(sats_str)
        except Exception as e:
            self.get_logger().warn(f"Bad GPS payload '{payload}': {e}")
            return

        # 构造并发布自定义消息
        msg = GpsSimple()
        msg.latitude = lat
        msg.longitude = lon
        msg.satellites = sats

        self.pub_gps.publish(msg)
        self.get_logger().info(
            f"GPS msg published: lat={lat:.8f}, lon={lon:.8f}, sats={sats}"
        )

    # 新增：处理颜色告警
    def handle_color_payload(self, payload: str):
        text = payload.strip().upper()
        now = time.time()

        if "RED" in text:
            # 冷却时间内就不重复播
            if now - self.last_red_play > self.play_cooldown:
                self.play_sound(self.red_audio, "RED")
                self.last_red_play = now
            else:
                self.get_logger().info("RED alert received but in cooldown.")
        elif "YELLOW" in text:
            if now - self.last_yellow_play > self.play_cooldown:
                self.play_sound(self.yellow_audio, "YELLOW")
                self.last_yellow_play = now
            else:
                self.get_logger().info("YELLOW alert received but in cooldown.")
        else:
            self.get_logger().info(f"Unknown color payload: '{payload}'")

    def loop_once(self):
        # ====== 读取树莓派发来的数据，解析 ======
        try:
            data = self.ser.read(1024)
        except Exception as e:
            self.get_logger().error(f"Serial read error: {e}")
            return

        if not data:
            return

        self.rx_buffer.extend(data)

        while True:
            if len(self.rx_buffer) < 5:
                break

            pos = self.rx_buffer.find(FRAME_HEADER)
            if pos == -1:
                self.rx_buffer.clear()
                break

            if pos > 0:
                del self.rx_buffer[:pos]

            if len(self.rx_buffer) < 5:
                break

            length = self.rx_buffer[2]
            total = 3 + length + 1

            if len(self.rx_buffer) < total:
                break

            frame = bytes(self.rx_buffer[:total])
            del self.rx_buffer[:total]

            body = frame[2:-1]
            checksum = frame[-1]

            if (sum(body) & 0xFF) != checksum:
                self.get_logger().warn("Checksum error")
                continue

            msg_type = body[1]
            self.get_logger().info(f"DEBUG: msg_type raw byte = {msg_type} (hex={msg_type:02X})")
            payload = body[2:].decode(errors="ignore")

            # 0x02: GPS
            if msg_type == 0x02:
                self.handle_gps_payload(payload)

            # 0x03: 颜色告警（RED / YELLOW）
            elif msg_type == 0x03:
                self.get_logger().info(f"Recv COLOR alert from RPi: '{payload}'")
                self.handle_color_payload(payload)

            else:
                # 其他类型先简单打印
                self.get_logger().info(
                    f"Recv from RPi: type={msg_type}, msg='{payload}'"
                )

    def destroy_node(self):
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
        except Exception:
            pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = GpsSerialNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
