import threading
import time

class DelayedTask:
    def __init__(self, delay_seconds, task_func):
        self.delay_seconds = delay_seconds
        self.task_func = task_func
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run_task)
        self._thread.daemon = True

    def _run_task(self):
        while not self._stop_event.is_set():
            if not self._stop_event.wait(self.delay_seconds):
                # If wait returns False, it means timeout happened (not interrupted)
                # so we execute the task
                self.task_func()

    def start(self):
        self._thread.start()

    def cancel(self):
        # Set the stop event to interrupt the waiting
        self._stop_event.set()
        # Optionally, you can join the thread if you want to wait for its termination
        self._thread.join()
