#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from gps_interfaces.msg import GpsSimple
import asyncio
import websockets
import json

connected_clients = set()


class GpsWebsocketReceiverNode(Node):
    def __init__(self):
        super().__init__("gps_websocket_receiver_node")

        self.sub = self.create_subscription(
            GpsSimple,
            "gps/simple",
            self.gps_callback,
            10
        )

    def gps_callback(self, msg):
        data = {
            "lat": msg.latitude,
            "lon": msg.longitude,
            "sats": msg.satellites
        }
        # 推送数据给 ws 客户端
        asyncio.create_task(self.broadcast(data))

    async def broadcast(self, data):
        if not connected_clients:
            return
        msg = json.dumps(data)
        for ws in list(connected_clients):
            try:
                await ws.send(msg)
            except:
                connected_clients.remove(ws)


# ★★★ websockets 11+ handler 没有 path 参数 ★★★
async def websocket_handler(websocket):
    print("客户端连接")
    connected_clients.add(websocket)

    try:
        async for _ in websocket:
            pass
    except:
        pass
    finally:
        print("客户端断开")
        connected_clients.remove(websocket)


async def main_async():
    rclpy.init()
    node = GpsWebsocketReceiverNode()

    # 适配 websockets 11+（handler 只有一个参数）
    server = await websockets.serve(websocket_handler, "localhost", 8888)
    print("🚀 WebSocket 服务器已启动 ws://localhost:8888")

    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.1)
            await asyncio.sleep(0.01)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
        server.close()
        await server.wait_closed()


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()




