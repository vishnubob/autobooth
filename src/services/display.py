from . service import Service, ServiceClient
from .. engine.display import init_display, display_text, display_image

class DisplayService(Service):
    ServiceName = "display"

class DisplayClient(ServiceClient):
    ServiceName = "display"
    DefaultTimeout = 1000 * 60 * 2
    
"""
def display_text(text: str) -> bool:
    global display_engine
    display_engine.control.display_text(text)
    return True

def display_image(img_fn: str) -> bool:
    global display_engine
    display_engine.control.display_image(img_fn)
    return True

display_engine = None
"""

def start_service():
    #global display_engine
    init_display()
    service = DisplayService()
    service.start(register_rpc=(display_text, display_image))

if __name__ == "__main__":
    start_service()
