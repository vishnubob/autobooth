"""
This file contains the classes and methods used to start the API server and communicate with it
Find the communicate way in the message.py
"""

import uuid
import urllib.request
import urllib.parse
import requests
import time
import subprocess
import threading
import json
import random
from pathlib import Path

from .logger import DebugLog

logger = DebugLog()


#
class Task:
    """
    This class is used to queue prompts and edit the payload of a prompt
    It is just a tool class, You should define your own class to use it
    """

    @staticmethod
    def load_payload(path) -> dict:
        with open(path, 'r') as file:
            return json.load(file)

    @staticmethod
    def queue_prompt(prompt: dict, client_id: str, server_address: str,
                     random_seed: bool = True, default_seed: int = 666666) -> str:
        """This method is used to queue a prompt for execution, returns prompt_id"""

        random_seed = random.randint(1, 100000000) if random_seed else default_seed
        _prompt = prompt
        Task.replace_key_value(_prompt, 'seed', random_seed, ['GenerateImage', 'GenerateVideo'])
        logger.debug(f'Prompt Seed: {random_seed}')
        p = {"prompt": _prompt, "client_id": client_id}
        data = json.dumps(p).encode('utf-8')
        headers = {'Content-Type': 'application/json'}  # Set Content-Type header
        req = urllib.request.Request(f"{server_address}/prompt", data=data, headers=headers)

        res = json.loads(urllib.request.urlopen(req).read())
        return res['prompt_id']

    @staticmethod
    def interrupt_prompt(server_address):
        """This method is used to interrupt a prompt"""
        try:
            requests.post(f"{server_address}/interrupt")
        except Exception as e:
            logger.error(e)

    @staticmethod
    def replace_input_image(json_object: dict, new_image_name, class_type='LoadImage'):
        """This method is used to replace the input image of a prompt"""
        for key, value in json_object.items():
            if isinstance(value, dict):
                if value.get('class_type') == class_type:
                    value['inputs']['image'] = new_image_name

            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        Task.replace_input_image(item, new_image_name, class_type)

    @staticmethod
    def replace_key_value(json_object: dict,
                          target_key: str, new_value: float | str | int,
                          class_type_list=None, exclude=True):
        """This method is used to edit the payload of a prompt"""
        for key, value in json_object.items():
            if isinstance(value, dict):
                class_type = value.get('class_type')
                should_apply_logic = (
                        (exclude and (class_type_list is None or class_type not in class_type_list)) or
                        (not exclude and (class_type_list is not None and class_type in class_type_list))
                )
                # Apply the logic to replace the target key with the new value if conditions are met
                if should_apply_logic and target_key in value:
                    value[target_key] = new_value
                # Recurse vertically (into nested dictionaries)
                Task.replace_key_value(value, target_key, new_value, class_type_list, exclude)
            # Recurse sideways (into lists)
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        Task.replace_key_value(item, target_key, new_value, class_type_list, exclude)

    @staticmethod
    def upload_image(server_address, filepath, subfolder=None, folder_type=None, overwrite=False):
        """# This method is used to upload an image to the API server for use in img2img or controlnet"""
        try:
            url = f"{server_address}/upload/image"
            files = {'image': open(filepath, 'rb')}
            data = {
                'overwrite': str(overwrite).lower()
            }
            if subfolder:
                data['subfolder'] = subfolder
            if folder_type:
                data['type'] = folder_type
            response = requests.post(url, files=files, data=data)
            return response.json()
        except Exception as e:
            import sys
            exc_type, exc_value, exc_traceback = sys.exc_info()
            line_no = exc_traceback.tb_lineno
            error_message = f'upload_image - Unhandled error at line {line_no}: {str(e)}'
            logger.error(error_message)


class TestTask(Task):
    """This class is used to test the Task class"""

    @staticmethod
    def test_prompt_text2img(client_id, server_address):
        prompt = Task.load_payload(Path(__file__).parent.joinpath('work_json', 'text2img.json'))
        Task.queue_prompt(prompt, client_id, server_address)

    @staticmethod
    def test_prompt_img2img(client_id, server_address):
        prompt = Task.load_payload(Path(__file__).parent.joinpath('work_json', 'img2img.json'))
        Task.queue_prompt(prompt, client_id, server_address)


class ComfyUiThread(threading.Thread):
    """
    This class is used to start the API server in a separate thread
    I recommend using this class to access the API server
    """

    def __init__(self, **kwargs):

        threading.Thread.__init__(self)
        self.args = kwargs

        self.server = None

    def run(self):
        try:
            self.server = ComfyUiLocalServer(**self.args)
            # wait for server start (in local server), dirty way, different computer may need different time
            # build a websocket connect to check is better, but i am lazy
            time.sleep(5)
            logger.info('Server Connecting...')
            self.server.connect()

        except Exception as e:
            logger.error('Thread', e)
            time.sleep(1)

    def stop(self):
        self.server.kill()
        self.join()


class ServerBase:
    """This class is used to communicate with the API server"""
    app_name = 'COMFY_CONNECTOR'
    client_id = app_name + '-' + str(uuid.uuid4())

    # connect finished, so we can start to poll button in other thread
    poll_button = False

    ws = None

    def __init__(self, api_url: str = '127.0.0.1', url_port: int = 8188):
        if hasattr(self, 'initialized'): return

        self.url = api_url
        self.url_port = url_port
        self.server_address = f"http://{api_url}:{self.url_port}"
        logger.info(self.server_address)

        # start websocket client
        self.ws_address = f"ws://{api_url}:{self.url_port}/ws?clientId={self.client_id}"
        logger.debug(self.ws_address)

        from .message import MessageManager
        self.manager = MessageManager()  # store message
        self.setup()

    def connect(self):
        def on_message(ws, message):
            self.manager.update(message)
            # logger.debug(message)

        def on_open(ws):
            self.poll_button = True

        from websocket import WebSocketApp  # (https://github.com/websocket-client/websocket-client)
        self.ws = WebSocketApp(self.ws_address, on_message=on_message, on_open=on_open)
        logger.info('Connecting to websocket server...')
        self.initialized = True
        self.ws.run_forever()

    def kill(self):
        self.ws.close()

    @staticmethod
    def find_available_port(url, url_port: int):
        """If the initial port is already in use, this method finds an available port to start the API server on"""
        port = url_port
        while True:
            try:
                response = requests.get(f'http://{url}:{port}')
                if response.status_code != 200:
                    port += 1
                return port
            except requests.ConnectionError:
                return port

    def setup(self):
        """Set up the signal connections for the message manager"""
        self.manager.signal_progress.connect(self.on_process)
        self.manager.signal_finished.connect(self.on_finished)
        self.manager.signal_executing_node.connect(self.on_excuting_node)
        self.manager.signal_interrupted.connect(self.on_interrupted)

    def on_process(self, process: float):
        """Called when the API server sends a process update"""
        logger.debug(f'Process: {process}')

    def on_finished(self, sender):
        """Called when the API server sends a finished update"""
        logger.info(f'Finished')

    def on_excuting_node(self, node_name: str):
        """Called when the API server sends a executing node update"""
        logger.debug(f'Executing node: {node_name}')

    def on_interrupted(self):
        """Called when the API server sends a interrupted update"""
        logger.debug(f'Interrupted')


class ComfyUiLocalServer(ServerBase):
    """This class is used to start a local server, inherits from ServerBase"""
    _instance = None
    _process = None

    def __init__(self, comfyui_dir: str, api_url: str = '127.0.0.1', url_port: int = 8188):
        if comfyui_dir is None: return

        super().__init__(api_url, url_port)

        self.command_line = self.generate_command_line(comfyui_dir)
        self.url_port = self.find_available_port(api_url, url_port)
        self.server_address = f"http://{api_url}:{self.url_port}"

        self.start_process()
        self.initialized = True

    def generate_command_line(self, comfyui_dir):
        """Use to generate the command line to start the API server"""
        convert_path = lambda p: p.replace('\\', '/').replace(' ', '" "')

        python_exe = Path(comfyui_dir).joinpath('python_embeded', 'python.exe')
        comfyui_path = Path(comfyui_dir).joinpath('ComfyUI', 'main.py')
        cmd = f'''{convert_path(str(python_exe))} {convert_path(str(comfyui_path))}'''
        logger.debug(cmd)
        return cmd

    def start_process(self):  # This method is used to start the API server
        api_command_line = self.command_line + f" --port {self.url_port}"  # Add the port to the command line
        if self._process is None or self._process.poll() is not None:  # Check if the process is not running or has terminated for some reason
            # stop print to stdout
            self._process = subprocess.Popen(api_command_line.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logger.info("API process started with PID:", self._process.pid)
            time.sleep(0.5)  # Wait for 0.5 seconds before returning

    def kill(self):
        """This method is used to kill the API server"""
        if self._process is not None and self._process.poll() is None:
            self._process.kill()
            self._process = None
            logger.info("API process killed")
        super().kill()
