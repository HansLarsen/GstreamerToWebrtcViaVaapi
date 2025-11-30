#!/usr/bin/env python3

import depthai as dai
from threading import Thread

class VideoSaver(dai.node.HostNode):
    def __init__(self, *args, **kwargs):
        dai.node.HostNode.__init__(self, *args, **kwargs)
        self.file_handle = open('video.encoded', 'wb')
        
    def set_output(self, pipe):
        self.pipe = pipe

    def build(self, *args):
        self.link_args(*args)
        return self

    def process(self, frame):
        data_objekt = frame.getData()
        self.pipe(data_objekt)

class OakCamera:
    def __init__(self, pipe):
        self.device_info_ = dai.DeviceInfo('18443010D12E980F00')
        # self.device_info_ = dai.DeviceInfo('192.168.1.208')
        self.device_ = dai.Device(self.device_info_)
        self.pipeline_ = dai.Pipeline(self.device_)
        self.profile_ = dai.VideoEncoderProperties.Profile.H264_MAIN # or H265_MAIN, H264_MAIN

        if pipe == None:
            raise "Missing callback function"
        
        self.pipe_ = pipe

        self.FPS_ = 30
        self.Width_ = 1280
        self.Height_ = 800

        self.camRgb_ = self.pipeline_.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_A)
        self.output_ = self.camRgb_.requestOutput((self.Width_, self.Height_), type=dai.ImgFrame.Type.NV12)
        self.encoded_ = self.pipeline_.create(dai.node.VideoEncoder).build(self.output_,
                frameRate = self.FPS_,
                profile = self.profile_)
        self.saver_ = self.pipeline_.create(VideoSaver).build(self.encoded_.out)
        self.saver_.set_output(self.pipe_)
        
        print("Camera pipeline created")
        
    def start(self):
        # Connect to device and start pipeline
        self.pipeline_.start()
        print("Camera pipeline started")
        
        
if __name__ == "__main__":
    import time
    oak_camera = OakCamera(lambda data: print(data))
    time.sleep(10)