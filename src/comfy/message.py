"""
This file contains the message types that are sent from the ComfyUI Server
It also contains the MessageManager class which is used to parse the messages and emit signals using blinker
You can use the MessageManager class in a modal operator to draw or call functions based on the message type
"""

import json
from enum import Enum


class MessageTypeType(Enum):
    """Message types that pull from the ComfyUI Server

    -- Response examples --
    {"type": "status", "data": {"status": {"exec_info": {"queue_remaining": 1}}}}
    {"type": "executing", "data": {"node": "3", "prompt_id": "520eef7d-2b0c-4bd6-8637-53cdaf1c75ca"}}
    {"type": "execution_start", "data": {"prompt_id": "6db9d8b5-9744-4b5f-91ec-ca9792db3e7e"}}
    {"type": "execution_cached", "data": {"nodes": ["8", "5", "9", "6", "3", "7", "4"], "prompt_id": "6db9d8b5-9744-4b5f-91ec-ca9792db3e7e"}}
    {"type": "progress", "data": {"value": 1, "max": 1}}

    """
    STATUS = 'status'
    EXECUTING = 'executing'
    EXECUTION_START = 'execution_start'
    EXECUTION_CACHED = 'execution_cached'
    EXECUTION_INTERRUPTED = 'execution_interrupted'
    EXECUTION_ERROR = 'execution_error'
    PROGRESS = 'progress'


class MessageDataType(Enum):
    """Message data that pull from the ComfyUI Server"""
    TRACEBACK = 'traceback'
    NODES = 'nodes'
    STATUS = 'status'
    SID = 'sid'
    NODE = 'node'  # executing node
    PROMPT_ID = 'prompt_id'  # executing prompt id, use to get history
    VALUE = 'value'  # progress value
    MAX = 'max'  # progress max


class MessageManager:
    from blinker import Signal

    signal_queue_remaining = Signal()
    signal_executing_node = Signal()
    signal_progress = Signal()
    signal_finished = Signal()
    signal_interrupted = Signal()

    def __init__(self, message: str | None = None):
        self.msg_type = None
        self.data = None
        self.update(message)

    @staticmethod
    def parse_message(message: str):
        msg = json.loads(message)
        msg_type = msg['type']
        data = msg["data"]
        return msg_type, data

    def update(self, message: str):
        if not message:
            return
        msg_type, data = self.parse_message(message)
        self.msg_type = msg_type
        self.data = data

        self._set_executing_node()
        self._set_interrupted()
        self._set_progress()
        self._set_queue_remaining()
        self._set_finished()

    def _set_queue_remaining(self):
        if self.msg_type == MessageTypeType.STATUS.value:
            queue_remaining = self.data.get(MessageDataType.STATUS.value).get("exec_info").get("queue_remaining")
            self.signal_queue_remaining.send(queue_remaining)

    def _set_finished(self):
        if self.msg_type == MessageTypeType.EXECUTING.value:
            if not self.data.get(MessageDataType.NODE.value):
                self.finished = True
                self.signal_finished.send()
            else:
                self.finished = False

    def _set_executing_node(self):
        if self.msg_type == MessageTypeType.EXECUTING.value:
            executing_node = self.data[MessageDataType.NODE.value]
            self.signal_executing_node.send(executing_node)

    def _set_progress(self):
        if self.msg_type == MessageTypeType.PROGRESS.value:
            fake_max = 50  # if node execute time is too short, the progress bar will be 0, so set a fake process
            fac = fake_max / self.data["max"]
            progress = self.data["value"] * fac
            self.signal_progress.send(int(progress))

    def _set_interrupted(self):
        if self.msg_type == MessageTypeType.EXECUTION_INTERRUPTED.value:
            self.signal_interrupted.send()
