import asyncio
import websockets
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
import pathlib

# WebSocket connection set to store connected clients
connected_clients = set()

async def handle_websocket(websocket, path):
    # Register client
    connected_clients.add(websocket)
    print("Client connected")
    
    try:
        async for message in websocket:
            if message == "button_clicked":
                print("Button was clicked! (via WebSocket)")  # This prints to the Python console
                # You can broadcast to all clients if needed
                # await broadcast("Button was clicked!")
                
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")
    finally:
        # Unregister client
        connected_clients.remove(websocket)

async def broadcast(message):
    """Broadcast a message to all connected clients"""
    if connected_clients:
        await asyncio.wait([client.send(message) for client in connected_clients.copy()])

def start_websocket_server():
    """Start WebSocket server in a separate thread"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    start_server = websockets.serve(handle_websocket, "localhost", 8765)
    loop.run_until_complete(start_server)
    print("WebSocket server running on ws://localhost:8765")
    loop.run_forever()

class MyHTTPHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Read the HTML file
        html_file = pathlib.Path(__file__).parent / 'index.html'
        with open(html_file, 'r') as f:
            self.html = f.read()
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(self.html.encode())
        else:
            super().do_GET()

def start_http_server():
    """Start HTTP server"""
    PORT = 8000
    httpd = HTTPServer(("", PORT), MyHTTPHandler)
    httpd.allow_reuse_address = True
    print(f"HTTP server running at http://localhost:{PORT}")
    httpd.serve_forever()

if __name__ == "__main__":
    # Start WebSocket server in a separate thread
    ws_thread = threading.Thread(target=start_websocket_server, daemon=True)
    ws_thread.start()
    
    # Start HTTP server in the main thread
    try:
        start_http_server()
    except KeyboardInterrupt:
        print("\nServers stopped")