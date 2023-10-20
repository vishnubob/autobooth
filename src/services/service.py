import time
import socket
import threading
from zero import ZeroServer, ZeroClient
from . registry import ServiceRegistry

def get_host_ip_and_port():
    # Determine local machine's IP
    host_name = socket.gethostname()
    host_ip = socket.gethostbyname(host_name)
    
    # Determine an open port using the provided code
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()

    return host_ip, port

class Service:
    ServiceName = None
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Service, cls).__new__(cls)
        return cls._instance

    def __init__(self, service_name=None, host=None, port=None, registry_host='redis', registry_port=6379):
        if self.__class__._initialized:
            return
        self.service_name = service_name or self.ServiceName
        if host is None or port is None:
            host_port = get_host_ip_and_port()
            host = host or host_port[0]
            port = port or host_port[1]
        self.host = host
        self.port = port
        self.registry = ServiceRegistry(redis_host=registry_host, redis_port=registry_port)
        self.running = threading.Event()
        self.heartbeat_thread = threading.Thread(target=self.send_heartbeats)
        self.__class__._initialized = True

    def app_hook(self, app):
        pass

    def start(self, register_rpc=None):
        """
        Register the service and start sending heartbeats in a background thread.
        """
        assert register_rpc is not None
        self.app = ZeroServer(port=self.port)
        for func in register_rpc:
            self.app.register_rpc(func)
        self.app_hook(self.app)
        self.registry.register_service(self.service_name, self.host, self.port)
        self.running.set()
        self.heartbeat_thread.start()
        try:
            self.app.run(workers=1)
        finally:
            self.stop()

    def stop(self):
        """
        Stop the service and the heartbeat thread gracefully.
        """
        if self.running.is_set():
            self.running.clear()
            self.heartbeat_thread.join()

    def send_heartbeats(self):
        """
        Send heartbeats periodically (every second) as long as the service is running.
        """
        while self.running.is_set():
            self.registry.heartbeat(self.service_name)
            time.sleep(1)

    def __del__(self):
        """
        Destructor to handle the case when the main thread crashes or finishes.
        """
        self.stop()

class ServiceClient:
    ServiceName = None
    DefaultTimeout = 5000

    def __init__(self, registry_host='redis.lan', registry_port=6379):
        self.registry = ServiceRegistry(redis_host=registry_host, redis_port=registry_port)
        self.host, self.port = self.lookup_service_details()
        self.zero_client = ZeroClient(self.host, self.port, default_timeout=self.DefaultTimeout)

    def lookup_service_details(self):
        while True:
            host, port = self.registry.lookup_service(self.ServiceName)
            if host is None or port is None:
                time.sleep(1)
                continue
            return (host, port)

    def __call__(self, *args, **kw):
        return self.zero_client.call(*args, **kw)
