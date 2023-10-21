from . services.camera import CameraClient

cli = CameraClient()
cli('capture', None)
