#!/usr/bin/env python3
import serial
import time

PORT = "/dev/serial0"
BAUD = 115200

FRAME_HEADER = b'\xAA\x55'


def build_packet(msg_type: int, payload: bytes) -> bytes:
    length = 1 + len(payload)  # TYPE + PAYLOAD
    body = bytes([length, msg_type]) + payload
    checksum = sum(body) & 0xFF
    return FRAME_HEADER + body + bytes([checksum])


def main():
    ser = serial.Serial(PORT, BAUD, timeout=0.01)
    print(f"Serial opened: {PORT} @ {BAUD}")

    rx_buffer = bytearray()
    count = 0
    last_send = time.time()

    while True:
        # 1) 每秒发一包给 PC
        if time.time() - last_send >= 1.0:
            msg = f"HELLO_FROM_RPI #{count}"
            pkt = build_packet(0x01, msg.encode())
            ser.write(pkt)
            print("Sent:", msg)
            count += 1
            last_send = time.time()

        # 2) 接收来自 PC 的数据
        data = ser.read(1024)
        if data:
            print(f"[DEBUG] raw bytes from PC: {data!r}")  # <== 新增：打印原始字节
            rx_buffer.extend(data)

            while True:
                if len(rx_buffer) < 5:
                    break

                pos = rx_buffer.find(FRAME_HEADER)
                if pos == -1:
                    print("[DEBUG] header not found, drop buffer")
                    rx_buffer.clear()
                    break

                if pos > 0:
                    print(f"[DEBUG] skip {pos} leading bytes")
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
                    print("[DEBUG] checksum error, frame:", frame)
                    continue

                msg_type = body[1]
                payload = body[2:].decode(errors="ignore")
                print(f"Recv from PC: type={msg_type}, msg={payload}")

        time.sleep(0.005)


if __name__ == "__main__":
    main()
