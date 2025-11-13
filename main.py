import asyncio
from library.GStreamer_Camera import GStreamerCamera
import json
import aiohttp
from aiohttp import web, WSCloseCode
import asyncio
import pathlib
import paho.mqtt.client as mqtt
import threading
import time

class WebServer:
    _camera = None
    _app = None
    _app_runner = None
    _websockets = set()
    _mqtt_client = None
    _update_thread = None
    _forward = 0.0
    _turn = 0.0
    _last_time = time.time()
    _topic = "capra/robot/remote/wheel_in"

    def __init__(self):
        self._app = web.Application()
        self._camera = GStreamerCamera()
        
        # Pass WebServer reference to camera so it can send messages
        self._camera.set_websocket_manager(self)
        self._camera.create_pipeline()
        
        # Start GStreamer in background thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        asyncio.get_event_loop().run_in_executor(None, self._camera.get_loop().run)

        # Serve HTML
        html_file = pathlib.Path(__file__).parent / 'index.html'
        with open(html_file, 'r') as f:
            self.html = f.read()

        self._app.router.add_get('/', self.server_http)
        self._app.router.add_get('/ws', self.handle_websocket)

        self._app_runner = web.AppRunner(self._app)
        asyncio.get_event_loop().create_task(self.start())

        self._mqtt_client = mqtt.Client()

        self._update_thread = threading.Thread(target=self.update_controls_thread)
        self._update_thread.daemon = True
        self._update_thread.start()

    def update_controls_thread(self):
        while True:
            if self._last_time - time.time() > 0.2:
                self._forward = 0.0
                self._turn = 0.0

            control_msg = { "linear": { "x": self._forward }, "angular": { "z": self._turn } }
            self._mqtt_client.publish(self._topic, json.dumps(control_msg))
            time.sleep(0.05)

    async def start(self):
        await self._app_runner.setup()
        site = web.TCPSite(self._app_runner, '0.0.0.0', 8000)
        await site.start()
        print("HTTP server started at http://0.0.0.0:8000")

    async def server_http(self, request):
        return web.Response(text=self.html, content_type='text/html')
    
    async def handle_websocket(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        # Add to active connections
        self._websockets.add(ws)
        print(f"WebSocket connected. Total connections: {len(self._websockets)}")
        
        # Send all pending SDP and ICE data to the new client
        await self._camera.send_pending_data_to_client(ws)
        
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    if data.get('type') == 'gamepad-input':
                        if data.get('input') == 'speed':
                        # Handle control message
                            forward = data.get('value', 0.0)
                            self._forward = forward
                        elif data.get('input') == 'turn':
                            turn = data.get('value', 0.0)
                            self._turn = turn
                        self._last_time = time.time()
                    elif data.get('type') == 'test-mqtt-connection':
                        try:
                            self._mqtt_client.connect(data.get('settings').get('broker'), 1883, 60)
                            self._mqtt_client.loop_start()
                            print("Connected to: ", data.get('settings').get('broker'))
                            self._topic = data.get('settings').get('topic')
                            await ws.send_str(
                                json.dumps({
                                    "type": "mqtt-test-result",
                                    "success": True
                                })
                            )
                        except Exception as e:
                            print("Failed to connect to: ", data.get('settings').get('broker'))
                            await ws.send_str(
                                json.dumps({
                                    "type": "mqtt-test-result",
                                    "success": False
                                })
                            )
                    else:
                        # Forward message to camera for processing
                        await self._camera.handle_client_message(ws, data)
                    
        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            self._websockets.remove(ws)
            await ws.close()
            print(f"WebSocket disconnected. Total connections: {len(self._websockets)}")
        
        return ws

    def get_websockets(self):
        """Get all active WebSocket connections"""
        return self._websockets.copy()

    def server_loop(self):
        asyncio.get_event_loop().run_forever()

if __name__ == "__main__":    
    # Start HTTP server in the main thread
    try:
        web_server = WebServer()
        web_server.server_loop()
    except KeyboardInterrupt:
        print("\nServers stopped")