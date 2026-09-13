# EE351_Project

Real-time GPS localization and color treasure-hunt alert system built on **ROS 2**.

A small robot/car equipped with a **WHEELTEC G60 GPS module** streams its position to a PC over a custom serial frame protocol. On the PC, a ROS 2 workspace parses the frames, publishes the GPS data on a topic, forwards it over WebSocket, and displays it live on a **Baidu Map** web page. When the robot approaches one of the three pre-marked "treasure boxes" (red / yellow / green), a matching audio alert is played on the PC.

## System Architecture

```
[WHEELTEC G60 GPS] --NMEA--> [Raspberry Pi] --USB serial--> [PC: ROS 2] --topic gps/simple--> [WebSocket node] --ws://localhost:8888--> [Browser: Baidu Map]
                                                                              |
                                            (color alert, type 0x03) ------> aplay: red/yellow/green box sound
```

The system consists of two ends:

- **Raspberry Pi** (branch `raspberry-pi`): reads the G60 GPS module (NMEA @ 9600 baud), establishes a GPS origin with a median filter, and sends the current position to the PC once per second as a framed packet.
- **PC** (branch `pc`, default): a ROS 2 workspace that reads the serial stream, parses frames, publishes GPS data on topic `gps/simple`, broadcasts it via WebSocket, and renders it on a live Baidu Map page with three pre-marked treasure boxes.

## Repository Layout

```
EE351_Project/
├── src/
│   ├── gps_interfaces/          # ROS 2 message package
│   │   └── msg/GpsSimple.msg    # float64 latitude, float64 longitude, int32 satellites
│   └── gps_serial_pkg/          # ROS 2 Python package (PC side)
│       ├── gps_serial_pkg/
│       │   ├── gps_serial_node.py               # parse serial frames, publish GPS, play alerts
│       │   ├── gps_websocket_receiver_node.py   # subscribe gps/simple -> WebSocket broadcast
│       │   └── sounds/                          # red/yellow/green box alert wav files
│       └── launch/gps_system.launch.py          # one-command launch: 2 nodes + http.server 8080
└── web/
    └── map_realtime.html        # Baidu Map live tracker (WGS84 -> GCJ02 -> BD09)
```

Raspberry Pi side (branch `raspberry-pi`):

```
├── main.py             # two threads: GPS reader + serial sender (1 packet / second)
├── G60.py              # WHEELTEC G60 GPS driver (NMEA parsing)
├── origin.py           # establish GPS origin: warmup, sampling, median
├── rpi_serial_test.py  # serial test utility
└── wheeltec_gps.sh     # GPS serial device setup script
```

## Communication Protocol

Both ends share the same binary frame format:

```
AA 55 | LENGTH | TYPE | PAYLOAD | CHECKSUM
```

| Field    | Size (bytes) | Description                                   |
|----------|--------------|-----------------------------------------------|
| Header   | 2            | `0xAA 0x55`                                   |
| Length   | 1            | `1 + len(payload)` (TYPE + PAYLOAD)           |
| Type     | 1            | Message type                                  |
| Payload  | Length - 1   | Message body                                  |
| Checksum | 1            | `(sum(Length + Type + Payload)) & 0xFF`       |

### Message Types

| Type | Meaning       | Payload                                              |
|------|---------------|------------------------------------------------------|
| 0x02 | GPS data      | ASCII `"latitude,longitude,satellites"` (decimal degrees) |
| 0x03 | Color alert   | ASCII `"RED"` / `"YELLOW"` / `"GREEN"` → plays the matching box sound |

## Hardware Requirements

- WHEELTEC G60 GPS module (or any NMEA 0183 GPS)
- Raspberry Pi with UART enabled (e.g., `/dev/serial0`)
- PC with a USB-to-serial adapter (e.g., `/dev/ttyUSB0`)

## Dependencies

- Raspberry Pi: Python 3, `pyserial`
- PC: ROS 2 (e.g., Humble), Python packages: `pyserial`, `websockets`; `alsa-utils` (`aplay`) for audio alerts

## Getting Started

### 1. Raspberry Pi (sensor side)

```bash
git clone -b raspberry-pi https://github.com/wyh1309/EE351_Project.git
# make sure the GPS module is accessible at /dev/wheeltec_gps (see wheeltec_gps.sh)
python3 main.py
```

`main.py` first establishes a GPS origin (median of samples), then starts two threads: one reads the GPS continuously, the other sends the position to the PC every second.

### 2. PC (ROS 2 side)

> The code references the project at `~/EE351_Project`, so clone it there:

```bash
git clone -b pc https://github.com/wyh1309/EE351_Project.git ~/EE351_Project
cd ~/EE351_Project
colcon build
source install/setup.bash
ros2 launch gps_serial_pkg gps_system.launch.py
```

This launches:

1. `gps_serial_node` — reads `/dev/ttyUSB0` @ 115200, parses frames, publishes on `gps/simple`;
2. `gps_receiver_node` — subscribes `gps/simple` and broadcasts JSON over `ws://localhost:8888`;
3. a static HTTP server on port `8080` serving the `web/` directory.

### 3. Web Visualization

Open `http://localhost:8080/map_realtime.html` in a browser:

- a marker follows the robot's live position on Baidu Map (WebSocket updates);
- WGS84 → GCJ02 → BD09 coordinate conversion is applied so the position aligns with Baidu Map;
- three treasure boxes (red / yellow / green) are pre-marked on the map;
- when the PC receives a color alert, it plays the matching box sound (1-second cooldown prevents repeated playback).

> Replace the Baidu Map AK in `web/map_realtime.html` with your own if needed.

## Branches

| Branch            | Description                                  |
|-------------------|----------------------------------------------|
| `pc` (default)    | PC-side ROS 2 workspace                      |
| `pc-lyh`          | Personal development fork of `pc`            |
| `raspberry-pi`    | Raspberry Pi side code                       |
| `raspberry-pi-lyh`| Personal development fork of `raspberry-pi`  |

## Notes

- Both ends implement the same frame protocol (header `0xAA55` + checksum), so the link is symmetric and bidirectional.
- GPS data is sent once per second; invalid frames are skipped until a satellite lock is acquired.
- The audio subsystem uses `aplay` (non-blocking); install with `sudo apt install alsa-utils`.
