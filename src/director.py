import random
import time
from pprint import pprint

from . services.presence import PresenceClient
from . services.camera import CameraClient
from . services.display import DisplayClient
from . services.speech import SpeechClient
from . services.transcribe import TranscribeClient
from . dialog import PhotoboothDialog
from . imagegen import generate_composite
from . data import get_data_path

listening_path = get_data_path("audio", "listening.mp3")
not_listening_path = get_data_path("audio", "not_listening.mp3")

presence_service = PresenceClient()
camera_service = CameraClient()
display_service = DisplayClient()
speech_service = SpeechClient()
transcribe_service = TranscribeClient()

def get_people_count():
    return presence_service("get_person_count", None)
    #return 1

def speak(text):
    print("speaking...")
    return speech_service("speak", text)

def transcribe():
    print("transcribing...")
    speech_service("play_sound", listening_path)
    resp = transcribe_service("transcribe", None)
    speech_service("play_sound", not_listening_path)
    return resp

def capture():
    print("capturing...")
    return camera_service("capture", None)

def display_image(img_fn):
    print("displaying image...")
    return display_service("display_image", img_fn)

def run_dialog(people_count=None):
    dialog = PhotoboothDialog()

    user_message = None
    while True:
        people_count = get_people_count()
        if people_count == 0:
            print("No people")
            break
        result = dialog.get_response(people_count=people_count, message=user_message)
        pprint(result)
        if not result.continue_session:
            print("Result closed session")
            break
        if result.generate_background: 
            #img_fn = capture()
            prompt = result.generate_background.prompt
            comp_fn = generate_composite(img_fn, prompt)
            display_image(comp_fn)
        speak(result.message)
        if result.waiting_on == "ready":
            transcribe()
            img_fn = capture()
            user_message = "ready"
        else:
            user_message = transcribe()
        print(user_message)

def run():
    print("running")
    while True:
        people_count = get_people_count()
        if people_count > 0:
            run_dialog(people_count=people_count)
        else:
            time.sleep(1)

if __name__ == "__main__":
    run()
