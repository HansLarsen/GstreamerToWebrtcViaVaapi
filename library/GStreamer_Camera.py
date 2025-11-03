import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstWebRTC', '1.0')
gi.require_version('GstSdp', '1.0')
gi.require_version("GstRtspServer", "1.0")
from gi.repository import Gst, GstWebRTC, GstSdp, GLib, GstRtspServer
import json
import asyncio
import logging
import os
os.environ["GST_DEBUG"] = "webrtcbin:6"

class GStreamerCamera:
    def __init__(self):
        Gst.init(None)
        self.pipeline = None
        self.webrtcbin = None
        self.server = GstRtspServer.RTSPServer.new()
        self.server.props.service = "8554"
        self.server.attach(None)
        self._websocket_manager = None
        
        # Store SDP offer and ICE candidates for new clients
        self._pending_offer = None
        self._pending_ice_candidates = []
        self._is_offer_ready = False
        
    def set_websocket_manager(self, manager):
        """Set the WebSocket manager to send messages to clients"""
        self._websocket_manager = manager
        
    def create_pipeline(self, device="/dev/video0"):
        pipeline_str = (
            f"v4l2src device={device} ! "
            "video/x-raw,width=640,height=480,framerate=30/1 ! "  # Lower resolution
            "videoconvert ! "
            "queue max-size-buffers=1 ! "
            "vp8enc deadline=1 cpu-used=4 target-bitrate=2000000 ! "
            "rtpvp8pay ! "
            "application/x-rtp,media=video,encoding-name=VP8,payload=96 ! "
            "webrtcbin name=webrtcbin latency=0 bundle-policy=max-bundle stun-server=stun://stun.l.google.com:19302"
        )

        # Create and store pipeline
        self.pipeline = Gst.parse_launch(pipeline_str)
        self.webrtcbin = self.pipeline.get_by_name("webrtcbin")

        # Connect signals
        self.webrtcbin.connect("on-negotiation-needed", self.on_negotiation_needed)
        self.webrtcbin.connect("on-ice-candidate", self.on_ice_candidate)
        self.webrtcbin.connect("notify::connection-state", self.on_connection_state_change)

        # Start the pipeline
        self.pipeline.set_state(Gst.State.PLAYING)
        print("GStreamer pipeline created and playing.")

    def on_connection_state_change(self, webrtcbin, pspec):
        state = webrtcbin.get_property("connection-state")
        states = {0: "NEW", 1: "CONNECTING", 2: "CONNECTED", 3: "DISCONNECTED", 4: "FAILED", 5: "CLOSED"}
        print(f"WebRTC Connection State: {states.get(state, 'UNKNOWN')}")

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
        
        print("Local SDP offer set.")
        if offer.sdp is None:
            print("Failed to create SDP offer")
            return

        # Store the offer for new clients
        self._pending_offer = offer.sdp.as_text()
        self._is_offer_ready = True

        print("SDP offer created and stored for new clients")
    
    def on_ice_candidate(self, element, mlineindex, candidate):
        print(f"New ICE candidate: {candidate} (mlineindex={mlineindex})")
        # Store ICE candidate for new clients
        self._pending_ice_candidates.append((mlineindex, candidate))
    
    async def send_sdp_offer(self, ws, offer):
        message = {
            'type': 'sdp-offer',
            'sdp': offer
        }
        await ws.send_str(json.dumps(message))
        print("Sent SDP offer to client")
    
    async def send_ice_candidate(self, ws, mlineindex, candidate):
        message = {
            'type': 'ice-candidate',
            'candidate': candidate,
            'sdpMLineIndex': mlineindex
        }
        await ws.send_str(json.dumps(message))
    
    async def send_pending_data_to_client(self, ws):
        """Send all pending SDP offer and ICE candidates to a new client"""
        if self._is_offer_ready and self._pending_offer:
            await self.send_sdp_offer(ws, self._pending_offer)
            
        for mlineindex, candidate in self._pending_ice_candidates:
            await self.send_ice_candidate(ws, mlineindex, candidate)
            
        print(f"Sent all pending data to new client: {len(self._pending_ice_candidates)} ICE candidates")
    
    async def handle_client_message(self, ws, data):
        message_type = data.get('type')
        print(f"Received message from client: {message_type}")
        
        if message_type == 'sdp-answer':
            # Client sent SDP answer
            sdp_text = data['sdp']
            res, sdp_msg = GstSdp.SDPMessage.new_from_text(sdp_text)
            if res == GstSdp.SDPResult.OK:
                answer = GstWebRTC.WebRTCSessionDescription.new(
                    GstWebRTC.WebRTCSDPType.ANSWER, sdp_msg)
                promise = Gst.Promise.new()
                self.webrtcbin.emit("set-remote-description", answer, promise)
                print("Set remote SDP answer")
                
        elif message_type == 'ice-candidate':
            # Client sent ICE candidate
            candidate = data['candidate']
            sdp_mline_index = data['sdpMLineIndex']
            self.webrtcbin.emit("add-ice-candidate", sdp_mline_index, candidate)
            print("Added ICE candidate from client")