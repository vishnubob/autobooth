import logging
import locale
import os
import sys

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

def _capture() -> str:
    from gphoto2 import GPhoto2Error
    global camera_frontend
    image_path = new_capture_filename()
    last_error = None
    for retry in range(5):
        try:
            camera_frontend.capture(copy=True, fn_target=image_path)
            last_error = None
            break
        except GPhoto2Error as err:
            last_error = err
            print(f'GPhoto2Error: {str(err)}')
            camera_frontend = init_camera(reset=True)
    if last_error:
        raise last_error
    return image_path

def reset_camera():
    usb_path = camera.canon_path()
    camera.reset_usb(usb_path)

def init_camera(reset=False):
    global camera_object, camera_frontend
    if reset:
        reset_camera()
    camera_object = camera.Camera()
    camera_frontend = camera_object.open(name='canon')
    return camera_frontend

def capture() -> str:
    import gphoto2 as gp
    target_path = new_capture_filename()
    locale.setlocale(locale.LC_ALL, '')
    logging.basicConfig(
        format='%(levelname)s: %(name)s: %(message)s', level=logging.WARNING)
    callback_obj = gp.check_result(gp.use_python_logging())
    camera = gp.Camera()
    camera.init()
    print('Capturing image')
    file_path = camera.capture(gp.GP_CAPTURE_IMAGE)
    print('Camera file path: {0}/{1}'.format(file_path.folder, file_path.name))
    print('Copying image to', target_path)
    camera_file = camera.file_get(
        file_path.folder, file_path.name, gp.GP_FILE_TYPE_NORMAL)
    camera_file.save(target_path)
    camera.file_delete(file_path.folder, file_path.name)
    camera.exit()
    return target_path

def start_service():
    #init_camera()
    service = CameraService()
    service.start(register_rpc=(capture, ))

if __name__ == "__main__":
    start_service()
