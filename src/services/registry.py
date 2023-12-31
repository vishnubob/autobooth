import time
import redis

REDIS_DEFAULT_HOST = 'redis.lan'

def connect_redis(**kw):
    while True:
        try:
            redis_client = redis.StrictRedis(**kw, socket_connect_timeout=1)
            redis_client.ping()
            return redis_client
        except redis.exceptions.TimeoutError:
            print('Redis server is not available, retrying...')
            time.sleep(1)
            continue

class ServiceRegistry:
    def __init__(self, redis_host=REDIS_DEFAULT_HOST, redis_port=6379):
        self.redis = connect_redis(host=redis_host, port=redis_port, decode_responses=True)
        self.timeout = 10

    def register_service(self, service_name, host, port):
        """
        Register a service with its host and port.
        Also, it considers the service registration as a heartbeat.
        """
        key = f"service:{service_name}"
        value = f"{host}:{port}"

        # Set the service host:port and also set it as active with a timeout
        self.redis.set(key, value)
        self.redis.set(f"{key}:active", "true", ex=self.timeout)

    def heartbeat(self, service_name):
        """
        Update the service's last heartbeat.
        """
        key = f"service:{service_name}:active"
        self.redis.set(key, "true", ex=self.timeout)

    def lookup_service(self, service_name):
        """
        Lookup a service's host and port.
        Returns a tuple (host, port) or None if service is not registered.
        """
        key = f"service:{service_name}"
        value = self.redis.get(key)
        if value:
            host, port = value.split(":")
            return host, int(port)
        return None

    def is_service_active(self, service_name):
        """
        Check if a service is active based on its last heartbeat.
        Returns True if active, False otherwise.
        """
        key = f"service:{service_name}:active"
        return self.redis.exists(key)

if __name__ == "__main__":
    # Example Usage:
    registry = ServiceRegistry()
    # Register a service
    registry.register_service("web_service", "127.0.0.1", 8000)
    # Check if service is active
    print(registry.is_service_active("web_service"))  # True
    # After 10 seconds (assuming no heartbeats are sent)
    print(registry.is_service_active("web_service"))  # False
    # Sending a heartbeat for a service
    registry.heartbeat("web_service")
    # Lookup service details
    print(registry.lookup_service("web_service"))  # ('127.0.0.1', 8000)
