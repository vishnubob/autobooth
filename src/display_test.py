import time
from . services.display import DisplayClient

cli = DisplayClient()
for x in range(10):
    cli('display_text', str(x))
    time.sleep(1)
