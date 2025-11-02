from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from av import VideoFrame
import fractions
from library.camera import Camera
import asyncio

class CustomVideoStreamTrack(VideoStreamTrack):
    """
    A custom video track that captures frames from an OpenCV webcam.
    """
    _instance = None
    _camera_capture = Camera()
    _framecount = 0

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self.settings = {}
            self._initialized = True
        else:
            return
        
        super().__init__()

        if not self._camera_capture.is_opened():
            raise RuntimeError("Error: Could not open camera.")
        
        print("Webcam initialized")

    async def recv(self):
        """
        This method is called to get the next video frame.
        """

        while self._framecount == self._camera_capture.get_framecount():
            await asyncio.sleep(0.01)

        self._framecount = self._camera_capture.get_framecount()

        frame = self._camera_capture.get_frame()
        if frame is None:
            raise RuntimeError("Error: Could not read frame.")
        
        # Convert the OpenCV frame (BGR) to a format aiortc can use (RGB)
        video_frame = VideoFrame.from_ndarray(frame, format='rgb24')
        video_frame.pts = self._framecount
        video_frame.time_base = fractions.Fraction(1, 30)  # Use fractions for time_base

        return video_frame
    
    def start(self):
        print("Starting video stream track")

    def stop(self):
        print("Stopping video stream track")
        self._camera_capture.release()