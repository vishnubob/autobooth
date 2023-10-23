from . service import Service, ServiceClient

class DisplayService(Service):
    ServiceName = "display"

class DisplayClient(ServiceClient):
    ServiceName = "display"
    DefaultTimeout = 1000 * 60 * 2
    
def start_service():
    from .. engine.display import init_display, display_text, display_image
    init_display()
    service = DisplayService()
    service.start(register_rpc=(display_text, display_image))

if __name__ == "__main__":
    start_service()
