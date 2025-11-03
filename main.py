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
        self._camera.create_pipeline()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        asyncio.get_event_loop().run_in_executor(None, self._camera.get_loop().run)

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
        print("HTTP server started at http://")

    async def server_http(self, request):
        return web.Response(text=self.html, content_type='text/html')
    
    async def handle_websocket(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    # Handle incoming messages if needed
        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            await ws.close()
        
        return ws

    def server_loop(self):
        asyncio.get_event_loop().run_forever()

if __name__ == "__main__":    
    # Start HTTP server in the main thread
    try:
        web_server = WebServer()
        web_server.server_loop()
    except KeyboardInterrupt:
        print("\nServers stopped")