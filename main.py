#!/usr/bin/env python3
import time
import threading
import serial

from G60 import GPS
from origin import establish_origin

# ---- 串口到 PC 的参数（就是你之前用来连 USB-TTL 的那个） ----
PC_PORT = "/dev/serial0"     
PC_BAUD = 115200

# ---- 帧协议 ----
FRAME_HEADER = b'\xAA\x55'

def build_packet(msg_type: int, payload: bytes) -> bytes:
    """
    AA 55 + LENGTH + TYPE + PAYLOAD + CHECKSUM
    LENGTH = TYPE(1) + PAYLOAD(len)
    CHECKSUM = sum(LENGTH + TYPE + PAYLOAD) & 0xFF
    """
    length = 1 + len(payload)
    body = bytes([length, msg_type]) + payload
    checksum = sum(body) & 0xFF
    return FRAME_HEADER + body + bytes([checksum])


# ---- 共享状态：最新 GPS 数据 ----
latest_gps = {
    "lat": None,   # float, 十进制度
    "lon": None,   # float, 十进制度
    "sats": None,  # int, 卫星个数
}
gps_lock = threading.Lock()
running = True


# ==================== 线程 1：持续读 GPS 串口 ====================

def gps_thread_func():
    global running
    gps = GPS(port="/dev/wheeltec_gps", baud=9600, timeout=1.0)
    print("[GPS] Opened /dev/wheeltec_gps @ 9600")

    try:
        while running:
            try:
                ret = gps.GPS_read()   # 逐行解析 NMEA，只对 GGA/VTG 生效
            except Exception as e:
                print("[GPS] read error:", e)
                time.sleep(0.1)
                continue

            # ret == 1 代表刚刚解析到一条有效的 GGA
            if ret == 1:
                try:
                    # G60 里 Convert_to_degrees 已经用 N/S/E/W 改成带符号的十进制度
                    lat = float(gps.lat)       # 字符串 -> float
                    lon = float(gps.lon)
                    sats = int(gps.numSv or 0)
                except Exception:
                    # 转换失败就忽略这一帧
                    continue

                with gps_lock:
                    latest_gps["lat"] = lat
                    latest_gps["lon"] = lon
                    latest_gps["sats"] = sats

                # 调试用，可以注释掉
                print(f"[GPS] lat={lat:.8f}, lon={lon:.8f}, sats={sats}")

            # 防止死循环占满 CPU
            time.sleep(0.01)

    finally:
        gps.GPS_stop()
        print("[GPS] stopped")


# ==================== 线程 2：定时把 GPS 发给 PC ====================

def serial_thread_func():
    global running
    ser = serial.Serial(PC_PORT, PC_BAUD, timeout=0.01)
    print(f"[PC] Serial opened: {PC_PORT} @ {PC_BAUD}")

    rx_buffer = bytearray()
    last_send = 0.0

    try:
        while running:
            now = time.time()

            # 每 1 秒发送一次 GPS 信息
            if now - last_send >= 1.0:
                with gps_lock:
                    lat = latest_gps["lat"]
                    lon = latest_gps["lon"]
                    sats = latest_gps["sats"]

                if lat is not None and lon is not None and sats is not None:
                    # 简单 payload 格式： "lat,lon,sats"
                    payload_str = f"{lat:.8f},{lon:.8f},{sats:d}"
                    pkt = build_packet(0x02, payload_str.encode("ascii"))
                    ser.write(pkt)
                    print("[PC] Sent GPS:", payload_str)
                else:
                    # 还没锁定 / 没有合格数据时就暂时不发
                    print("[PC] No valid GPS yet, skip send")

                last_send = now

            # --------（可选）接收来自 PC 的其它帧，沿用你之前的解析逻辑 --------
            data = ser.read(1024)
            if data:
                rx_buffer.extend(data)
                while True:
                    if len(rx_buffer) < 5:
                        break

                    pos = rx_buffer.find(FRAME_HEADER)
                    if pos == -1:
                        rx_buffer.clear()
                        break

                    if pos > 0:
                        del rx_buffer[:pos]

                    if len(rx_buffer) < 5:
                        break

                    length = rx_buffer[2]
                    total = 3 + length + 1
                    if len(rx_buffer) < total:
                        break

                    frame = bytes(rx_buffer[:total])
                    del rx_buffer[:total]

                    body = frame[2:-1]
                    checksum = frame[-1]
                    if (sum(body) & 0xFF) != checksum:
                        print("[PC] checksum error")
                        continue

                    msg_type = body[1]
                    payload = body[2:].decode(errors="ignore")
                    print(f"[PC] Recv from PC: type={msg_type}, msg={payload}")

            time.sleep(0.005)

    finally:
        ser.close()
        print("[PC] serial closed")


# ==================== 主线程：启动/停止两个子线程 ====================

if __name__ == "__main__":

    # ---- 第一步：初始化 GPS 实例（暂不进入线程） ----
    gps_init = GPS(port="/dev/wheeltec_gps", baud=9600, timeout=1.0)
    print("[MAIN] 开始建立 GPS 原点...")

    lat0, lon0 = establish_origin(gps_init)
    print(f"[MAIN] GPS 原点建立完成 lat0={lat0}, lon0={lon0}")

    gps_init.GPS_stop()   # 初始化占用的串口关闭，线程重新打开

    # ---- 第二步：正常启动两个线程 ----
    gps_thread = threading.Thread(target=gps_thread_func, daemon=True)
    pc_thread = threading.Thread(target=serial_thread_func, daemon=True)

    gps_thread.start()
    pc_thread.start()


    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[MAIN] Ctrl+C, stopping...")
        running = False
        gps_thread.join()
        pc_thread.join()
        print("[MAIN] exit")
