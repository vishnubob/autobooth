# XXX: monkey patch

class NodeTree:
    """NodeTree class is a simple class to find nodes in a tree"""

    @staticmethod
    def find_output_node(payload) -> str | None:
        """This method is used to find the node containing the SaveImage class in a prompt"""
        for key, value in payload.items():
            if not isinstance(value, dict): continue

            if value.get("class_type") == "SaveImage":
                return key
            result = NodeTree.find_output_node(value)
            if result:
                return result
        return None

from . import comfy
comfy.data.NodeTree = NodeTree

import os
import threading
import json
import time
from . comfy.server import ServerBase, Task
from . comfy.data import History, NodeTree
import blinker

server_address = os.environ.get('COMFY_SERVER_ADDRESS', 'localhost')
server_port = os.environ.get('COMFY_SERVER_PORT', '8188')
autobooth_template_jsfn = os.path.join(os.path.dirname(__file__), 'comfy', 'autobooth_sdxl_api.json')

class ComfyServer(threading.Thread):
    def __init__(self, **kwargs):
        threading.Thread.__init__(self)
        self.daemon = True
        self.args = kwargs
        self.server = None

    def run(self):
        self.server = ServerBase(**self.args)
        self.server.connect()

    def stop(self):
        self.server.kill()
        self.join()

    def submit(self, prompt):
        return Task.queue_prompt(prompt, self.server.client_id, self.server.server_address)

    def get_history(self, prompt_id):
        return History(self.server.server_address, prompt_id)
    
    def upload_image(self, imgfn, overwrite=True):
        return Task.upload_image(self.server.server_address, imgfn, overwrite=overwrite)


server = ComfyServer(api_url=server_address, url_port=server_port)

def generate_composite(img_fn, prompt):
    if server.server is None:
        server.start()
        time.sleep(2)
    (path, ext) = img_fn.split('.')
    target_fn = f'{path}-composite.{ext}'

    finished = threading.Event()
    def notify_finish(sender):
        finished.set()

    with open(autobooth_template_jsfn) as fh:
        template = json.load(fh)

    style = '35mm photograph, film, professional, 4k, highly detailed, HDR'
    pos_prompt = f'{prompt} {style}'
    neg_prompt = 'drawing, painting, crayon, sketch, graphite, impressionist, noisy, blurry, soft, deformed, ugly, person, people, text, watermark, NSFW, nudity'

    template['75']['inputs']['text_g'] = pos_prompt
    template['75']['inputs']['text_l'] = pos_prompt
    template['76']['inputs']['text'] = pos_prompt

    template['79']['inputs']['text_g'] = neg_prompt
    template['79']['inputs']['text_l'] = neg_prompt
    template['86']['inputs']['text'] = neg_prompt

    template['46']['inputs']['image'] = os.path.split(img_fn)[-1]

    res = server.upload_image(img_fn)
    server.server.manager.signal_finished.connect(notify_finish)

    prompt_id = server.submit(template)
    while not finished.is_set():
        finished.wait(.1)

    server.server.manager.signal_finished.disconnect(notify_finish)

    history = server.get_history(prompt_id)
    history.save_latest_image(template, target_fn)
    return target_fn
