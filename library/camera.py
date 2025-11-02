import cv2

class Camera:
    def __init__(self, camera_index=0):
        self.cap = cv2.VideoCapture(camera_index)
        self.frame_count = 0

        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        # Try to reduce buffering for lower latency
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    def get_frame(self):
        ret, frame = self.cap.read()
        self.frame_count += 1
        if not ret:
            return None
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return rgb

    def release(self):
        self.cap.release()

    def is_opened(self):
        return self.cap.isOpened()
    
    def get_frame_count(self):
        return self.frame_count
        
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