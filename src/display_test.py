import time
from . services.display import DisplayClient

img_fn = '/nfs/photobooth/data/1080p_test.png'

cli = DisplayClient()
for x in range(10):
    cli('display_text', str(x))
    time.sleep(.1)

cli('display_image', img_fn)
