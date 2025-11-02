import asyncio
import websockets
import threading
import cv2
import json
from http.server import HTTPServer, SimpleHTTPRequestHandler
import pathlib
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.media import MediaPlayer
from av import VideoFrame
import fractions
from library.camera import Camera
import os
from aiortc import RTCIceCandidate

ROOT = os.path.dirname(__file__)

# WebRTC configuration
pcs = set()  # Set to track peer connections
camera_capture = Camera()

class CustomVideoStreamTrack(VideoStreamTrack):
    """
    A custom video track that captures frames from an OpenCV webcam.
    """
    def __init__(self, camera_id=0):
        global camera_capture
        super().__init__()

        print("Webcam initialized")

        if not camera_capture.is_opened():
            raise RuntimeError("Error: Could not open camera.")

    async def recv(self):
        """
        This method is called to get the next video frame.
        """
        global camera_capture
        frame = camera_capture.get_frame()
        if frame is None:
            raise RuntimeError("Error: Could not read frame.")
        
        # Convert the OpenCV frame (BGR) to a format aiortc can use (RGB)
        video_frame = VideoFrame.from_ndarray(frame, format='rgb24')
        video_frame.pts = camera_capture.get_frame_count()
        video_frame.time_base = fractions.Fraction(1, 30)  # Use fractions for time_base

        return video_frame
    
    def start(self):
        print("Starting video stream track")

    def stop(self):
        print("Stopping video stream track")
        camera_capture.release()

async def handle_websocket(websocket, path):
    print("Client connected")
    
    # Create a new RTCPeerConnection for this client
    pc = RTCPeerConnection()
    pcs.add(pc)
    
    # Add the video track to the connection
    video_track = CustomVideoStreamTrack()
    pc.addTransceiver(video_track, direction="sendonly")

    for transceiver in pc.getTransceivers():
        print(f"Transceiver: {transceiver.kind}, Direction: {transceiver.direction}")

    @pc.on("iceconnectionstatechange")
    async def on_iceconnectionstatechange():
        print(f"ICE connection state is {pc.iceConnectionState}")
        if pc.iceConnectionState == "failed":
            await pc.close()
            pcs.discard(pc)

    @pc.on("track")
    def on_track(track):
        print(f"Track {track.kind} received")
    
    try:
        async for message in websocket:
            if message == "button_clicked":
                print("Button was clicked! (via WebSocket)")
            else:
                # Handle WebRTC signaling messages
                data = json.loads(message)
                
                if data["type"] == "offer":

                    print("Received SDP Offer:", data["sdp"])
                    # Set the remote description and create answer
                    offset_sdp = RTCSessionDescription(sdp=data["sdp"], type=data["type"])
                    await pc.setRemoteDescription(
                        offset_sdp
                    )
                    
                    # Create and set local description
                    answer = await pc.createAnswer()
                    print("Sending sdp awnser: ", answer.sdp)
                    await pc.setLocalDescription(answer)
                    
                    # Send the answer back to the client
                    await websocket.send(json.dumps({
                        "type": "answer",
                        "sdp": pc.localDescription.sdp
                    }))
                
    except Exception as e:
        print(f"{e}")
    finally:
        # Clean up
        await pc.close()
        pcs.discard(pc)
        print("Client disconnected")

def start_websocket_server():
    """Start WebSocket server in a separate thread"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    start_server = websockets.serve(handle_websocket, "0.0.0.0", 8765)  # Use 0.0.0.0 to allow external connections
    loop.run_until_complete(start_server)
    print("WebSocket server running on ws://0.0.0.0:8765")
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
    httpd = HTTPServer(("0.0.0.0", PORT), MyHTTPHandler)  # Use 0.0.0.0 to allow external connections
    httpd.allow_reuse_address = True
    print(f"HTTP server running at http://0.0.0.0:{PORT}")
    httpd.serve_forever()

async def shutdown():
    """Cleanup when shutting down"""
    # Close all peer connections
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()

if __name__ == "__main__":
    # Start WebSocket server in a separate thread
    ws_thread = threading.Thread(target=start_websocket_server, daemon=True)
    ws_thread.start()
    
    # Start HTTP server in the main thread
    try:
        start_http_server()
    except KeyboardInterrupt:
        print("\nServers stopped")