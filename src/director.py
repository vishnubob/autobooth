import random
import time
from pprint import pprint

import ast
import json
import replicate

from . services.presence import PresenceClient
from . services.camera import CameraClient
from . services.display import DisplayClient
from . services.speech import SpeechClient
from . services.transcribe import TranscribeClient
from . dialog import PhotoboothDialog
from . imagegen import generate_composite
from . data import get_data_path
from . delay import DelayedTask

listening_path = get_data_path("audio", "listening.mp3")
not_listening_path = get_data_path("audio", "not_listening.mp3")

#presence_service = PresenceClient()
camera_service = CameraClient()
display_service = DisplayClient()
speech_service = SpeechClient()
transcribe_service = TranscribeClient()

#def get_people_count():
    #return presence_service("get_person_count", None)
    #return 1

def get_people_count(image_fn):
    print('people counting')
    deployment = replicate.deployments.get("vishnubob/yolo")
    with open(image_fn, 'rb') as fh:
        prediction = deployment.predictions.create(
            input={
                "input_image": fh,
                "return_json": True,
            })
        prediction.wait()
        result = json.loads(prediction.output['json_str'])
        try:
            result = ast.literal_eval(result)
        except SyntaxError:
            print(result)
            result = {}
        count = 0
        for res in result.values():
            if res['cls'] == 'person':
                count += 1
        print(f'there are {count} people')
        return count

def speak(text):
    print("speaking...")
    return speech_service("speak", text)

def calibrate():
    print('calibrating microphone')
    return transcribe_service("calibrate", None)

def transcribe(indicate=True):
    print("transcribing...")
    if indicate:
        speech_service("play_sound", listening_path)
    resp = transcribe_service("transcribe", None)
    if indicate:
        speech_service("play_sound", not_listening_path)
    return resp

def capture():
    print("capturing...")
    return camera_service("capture", None)

def display_image(img_fn):
    print("displaying image...")
    return display_service("display_image", img_fn)

def wait_on_hello():
    while True:
        energy = calibrate()
        print(energy)
        user_message = transcribe(indicate=False)
        print(user_message)
        if 'hello' in user_message.lower():
            speech_service('speak', 'Hello, please wait a moment')
            img_fn = capture()
            #img_fn = '/home/ghall/duo-2-mask.png'
            return get_people_count(img_fn)

def run_dialog(people_count=None):
    dialog = PhotoboothDialog()

    user_message = None
    while True:
        result = dialog.get_response(people_count=people_count, message=user_message)
        pprint(result)
        if not result.continue_session or result.waiting_on is None:
            speak(result.message)
            print("Result closed session")
            break
        if result.generate_background: 
            prompt = result.generate_background.prompt
            comp_fn = generate_composite(img_fn, prompt)
            display_image(comp_fn)
        elif people_count == 0:
            print("No people")
            break
        speak(result.message)
        if result.waiting_on == "ready":
            display_image('/nfs/photobooth/data/plain-black-background.jpg')
            transcribe()
            img_fn = capture()
            people_count = get_people_count(img_fn)
            print(people_count)
            user_message = "ready"
        else:
            user_message = transcribe()
        print(user_message)

def loop():
    print("loop()")
    display_image('/nfs/photobooth/data/plain-black-background.jpg')
    flash_warmup = DelayedTask(30 * 60, capture)
    flash_warmup.start()
    people_count = -1
    while people_count <= 0:
        #time.sleep(1)
        people_count = wait_on_hello()
    flash_warmup.cancel()
    run_dialog(people_count=people_count)

def run():
    while True:
        loop()

if __name__ == "__main__":
    run()
