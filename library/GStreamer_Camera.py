import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstWebRTC', '1.0')
gi.require_version('GstSdp', '1.0')
gi.require_version("GstRtspServer", "1.0")
from gi.repository import Gst, GstWebRTC, GstSdp, GLib, GstRtspServer
import json
import asyncio

class GStreamerCamera:
    def __init__(self):
        Gst.init(None)
        self.pipeline = None
        self.server = GstRtspServer.RTSPServer.new()
        self.server.props.service = "8554"
        self.server.attach(None)
        
    def create_pipeline(self, device="/dev/video0"):
        pipeline_str = (
            f"v4l2src device={device} ! "
            "image/jpeg,width=1280,height=720,framerate=30/1 ! "
            "jpegdec ! "
            "videoconvert ! "
            "video/x-raw,format=NV12 ! "
            "vaapipostproc ! "
            "vaapih264enc ! "
            "h264parse config-interval=1 ! "
            "rtph264pay name=pay0 pt=96"
        )
        
        self.factory = GstRtspServer.RTSPMediaFactory.new()
        self.factory.set_launch(pipeline_str)
        self.factory.set_shared(True)
        self.server.get_mount_points().add_factory("/camera", self.factory)
        print("RTSP server is live at rtsp://0.0.0.0:8554/camera")

    def get_loop(self):
        return GLib.MainLoop()