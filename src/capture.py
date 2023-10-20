import time
import camera

canon_path = camera.canon_path()
camera.reset_usb(canon_path)
#time.sleep(1)
#cam = camera.Camera()
#frontend = cam.open()
#fp = frontend.capture(copy=True)
#print(fp)
