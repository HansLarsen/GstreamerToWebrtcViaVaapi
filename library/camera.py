import cv2
import threading
import time

class Camera:
    _framecount = 0
    _frame = None
    _cap = None
    _running = False
    _thread = None

    def __init__(self):
        pipeline = (
            "v4l2src device=/dev/video0 ! video/x-raw,framerate=30/1,width=640,height=480 ! "
            "videoconvert ! appsink sync=false max-lateness=10000000"
        )
        self._cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        self._frame = None
        self._running = True

        self._cap.set(cv2.CAP_PROP_FPS, 30)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self._cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # Manual mode
        self._cap.set(cv2.CAP_PROP_AUTO_WB, 0)          # Disable auto white balance

        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def _capture_loop(self):
        while self._running:
            ret, frame = self._cap.read()
            if ret:
                self._framecount += 1
                self._frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:
                print("Warning: Could not read frame from camera.")

    def get_frame(self):
        return self._frame
    
    def get_framecount(self):
        return self._framecount

    def release(self):
        self._running = False
        self._thread.join()
        self._cap.release()

    def is_opened(self):
        return self._cap.isOpened()
        
if __name__ == "__main__":
    camera = Camera()
    if not camera.is_opened():
        print("Error: Could not open camera.")
        exit()

    frame = camera.get_frame()
    if frame is None:
        print("Error: Could not read frame.")
        exit(1)

    cv2.imwrite('frame.png', cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))

    camera.release()
    cv2.destroyAllWindows()
    exit(0)