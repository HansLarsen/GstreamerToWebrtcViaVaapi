import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstWebRTC', '1.0')
gi.require_version('GstSdp', '1.0')
gi.require_version("GstRtspServer", "1.0")
from gi.repository import Gst, GstWebRTC, GstSdp, GLib, GstRtspServer
import json
import asyncio
import logging

class GStreamerCamera:
    _websocket = None

    def __init__(self):
        Gst.init(None)
        self.pipeline = None
        self.server = GstRtspServer.RTSPServer.new()
        self.server.props.service = "8554"
        self.server.attach(None)
        self._websocket = None
        
    def create_pipeline(self, device="/dev/video0"):
        pipeline_str = (
            f"v4l2src device={device} ! "
            "image/jpeg,width=1280,height=720,framerate=30/1 ! "
            "vaapijpegdec ! "
            "vaapipostproc ! "
            "vaapih264enc ! "
            "h264parse config-interval=1 ! "
            "rtph264pay pt=96 ! "
            "application/x-rtp,media=video,encoding-name=H264,payload=96 ! "
            "webrtcbin name=webrtcbin latency=0 bundle-policy=max-bundle stun-server=stun://stun.l.google.com:19302"
        )
        
        # GStreamer Pipeline starts
        pipeline = Gst.parse_launch(pipeline_str)
        webrtcbin = pipeline.get_by_name("webrtcbin")

        # Connect signals
        webrtcbin.connect("on-negotiation-needed", self.on_negotiation_needed)
        webrtcbin.connect("on-ice-candidate", self.on_ice_candidate)

        print("GStreamer pipeline created.")

    def get_loop(self):
        return GLib.MainLoop()
    
    def on_negotiation_needed(self, element):
        logging.info("Creating SDP offer...")
        promise = Gst.Promise.new_with_change_func(self.on_offer_created, element, None)
        element.emit("create-offer", None, promise)
    
    def on_offer_created(self, promise, element, *args):
        reply = promise.get_reply()
        offer = reply.get_value('offer')
        
        # Set local description
        promise = Gst.Promise.new()
        element.emit("set-local-description", offer, promise)
        
        # Send offer to all connected clients
        for ws in self._websocket.keys():
            asyncio.create_task(self.send_sdp_offer(ws, offer))
    
    def on_ice_candidate(self, element, mlineindex, candidate):
        # Send ICE candidate to all clients
        for ws in self._websocket.keys():
            asyncio.create_task(self.send_ice_candidate(ws, mlineindex, candidate))
    
    async def send_sdp_offer(self, ws, offer):
        message = {
            'type': 'sdp-offer',
            'sdp': offer.sdp.as_text()
        }
        await ws.send_str(json.dumps(message))
    
    async def send_ice_candidate(self, ws, mlineindex, candidate):
        message = {
            'type': 'ice-candidate',
            'candidate': candidate,
            'sdpMLineIndex': mlineindex
        }
        await ws.send_str(json.dumps(message))
    
    async def handle_client_message(self, ws, data):
        message_type = data.get('type')
        
        if message_type == 'sdp-answer':
            # Client sent SDP answer
            sdp_text = data['sdp']
            res, sdp_msg = GstSdp.SDPMessage.new_from_text(sdp_text)
            if res == GstSdp.SDPResult.OK:
                answer = GstWebRTC.WebRTCSessionDescription.new(
                    GstWebRTC.WebRTCSDPType.ANSWER, sdp_msg)
                promise = Gst.Promise.new()
                self.webrtcbin.emit("set-remote-description", answer, promise)
                
        elif message_type == 'ice-candidate':
            # Client sent ICE candidate
            candidate = data['candidate']
            sdp_mline_index = data['sdpMLineIndex']
            self.webrtcbin.emit("add-ice-candidate", sdp_mline_index, candidate)
