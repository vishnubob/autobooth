from . service import Service, ServiceClient
from .. engine.yolo import YoloWorker

class PresenceService(Service):
    ServiceName = "presence"

class PresenceClient(ServiceClient):
    ServiceName = "presence"
    DefaultTimeout = 1000 * 60 * 2
    
yolo_worker = None

def get_person_count() -> int:
    global yolo_worker
    return yolo_worker.get_person_count()

def start_service():
    global yolo_worker
    yolo_worker = YoloWorker()
    yolo_worker.start()
    service = PresenceService()
    service.start(register_rpc=(get_person_count, ))

if __name__ == "__main__":
    start_service()
