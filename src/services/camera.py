import time
from datetime import datetime
from .. engine import camera
from . service import Service, ServiceClient

def get_timestamp():
    fmt_string = '%h%d-%Y_%H-%M-%S'
    dt = datetime.now()
    return dt.strftime(fmt_string)

def new_capture_filename(ext='jpg', prefix='/nfs/photobooth/captures'):
    ts = get_timestamp()
    return f'{prefix}/capture_{ts}.{ext}'

class CameraService(Service):
    ServiceName = "camera"

class CameraClient(ServiceClient):
    ServiceName = "camera"
    DefaultTimeout = 1000 * 60 * 2
    
camera_object = None
camera_frontend = None

def capture() -> str:
    global camera_frontend
    image_path = new_capture_filename()
    camera_frontend.capture(copy=True, fn_target=image_path)
    return image_path

def init_camera():
    global camera_object, camera_frontend
    camera_object = camera.Camera()
    camera_frontend = camera_object.open(name='canon')

def start_service():
    init_camera()
    service = CameraService()
    service.start(register_rpc=(capture, ))

if __name__ == "__main__":
    start_service()
