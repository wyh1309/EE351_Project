#!/usr/bin/env python3
import serial
import time
from typing import Optional

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import NavSatFix, NavSatStatus

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
        self.pub_navsat = self.create_publisher(NavSatFix, "gps/fix", 10)

        # 定时器：周期性发测试消息给树莓派（可选）
        self.count = 0
        self.last_send = time.time()
        self.timer = self.create_timer(0.005, self.loop_once)

    def loop_once(self):
        now = time.time()

        # ====== 1) 每 2 秒给树莓派发一条测试消息（你原来的逻辑） ======
        if now - self.last_send >= 2.0:
            msg = f"HELLO_FROM_PC #{self.count}"
            pkt = build_packet(0x10, msg.encode())
            try:
                self.ser.write(pkt)
            except Exception as e:
                self.get_logger().error(f"Serial write error: {e}")
            else:
                self.get_logger().info(f"Sent: {msg}")
            self.count += 1
            self.last_send = now

        # ====== 2) 读取树莓派发来的数据，解析出 GPS 并发布 ======
        try:
            data = self.ser.read(1024)
        except Exception as e:
            self.get_logger().error(f"Serial read error: {e}")
            return

        if data:
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
                payload = body[2:].decode(errors="ignore")

                # 我们约定：树莓派发 GPS 的帧 msg_type = 0x02
                if msg_type == 0x02:
                    self.handle_gps_payload(payload)
                else:
                    # 其他类型先简单打印
                    self.get_logger().info(f"Recv from RPi: type={msg_type}, msg={payload}")

    def handle_gps_payload(self, payload: str):
        """
        payload 格式： "lat,lon,sats"
        例如： "30.12345678,120.12345678,10"
        """

        try:
            lat_str, lon_str, sats_str = payload.split(',')
            lat = float(lat_str)
            lon = float(lon_str)
            sats = int(sats_str)
        except Exception as e:
            self.get_logger().warn(f"Bad GPS payload '{payload}': {e}")
            return

        # 构造 NavSatFix 消息
        msg = NavSatFix()
        # 这里暂时不做坐标系转换，直接当作 WGS84
        msg.latitude = lat
        msg.longitude = lon
        msg.altitude = 0.0  # 如果以后树莓派也发高度，这里可以填真实值

        # status 里没有“卫星数”字段，我先借用 service 塞一下
        msg.status.status = NavSatStatus.STATUS_FIX
        msg.status.service = sats  # 纯自用，不是标准用法，但方便你调试

        # 协方差暂时给个 0 或 nan
        msg.position_covariance_type = NavSatFix.COVARIANCE_TYPE_UNKNOWN

        self.pub_navsat.publish(msg)
        self.get_logger().info(
            f"GPS: lat={lat:.8f}, lon={lon:.8f}, sats={sats}"
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
