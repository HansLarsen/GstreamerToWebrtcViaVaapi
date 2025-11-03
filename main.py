import asyncio
from library.GStreamer_Camera import GStreamerCamera
import json
import aiohttp
from aiohttp import web, WSCloseCode
import asyncio
import pathlib

class WebServer:
    _camera = None
    _app = None
    _app_runner = None
    _websockets = set()

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