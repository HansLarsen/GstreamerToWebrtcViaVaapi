import asyncio
import websockets
from http.server import HTTPServer
from library.HTTP_Server import MyHTTPHandler
from library.GStreamer_Camera import GStreamerCamera
import json

pcs = set()  # Set to track peer connections
camera = GStreamerCamera()

async def handle_websocket(websocket, path):
    # print("Client connected")
    await websocket.send("Successfully registered")

def start_websocket_server():
    """Start WebSocket server in a separate thread"""
    PORT = 8765
    start_server = websockets.serve(handle_websocket, "0.0.0.0", PORT)  # Use 0.0.0.0 to allow external connections
    asyncio.get_event_loop().run_until_complete(start_server)
    print(f"WebSocket server running on ws://0.0.0.0:{PORT}")

def start_http_server():
    """Start HTTP server"""
    PORT = 8000
    httpd = HTTPServer(("0.0.0.0", PORT), MyHTTPHandler)  # Use 0.0.0.0 to allow external connections
    httpd.allow_reuse_address = True
    print(f"HTTP server running at http://0.0.0.0:{PORT}")
    asyncio.get_event_loop().run_in_executor(None, httpd.serve_forever)

if __name__ == "__main__":    
    # Start HTTP server in the main thread
    camera.create_pipeline()
    try:
        start_websocket_server()
        start_http_server()
        asyncio.get_event_loop().run_until_complete(camera.get_loop().run())
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        print("\nServers stopped")