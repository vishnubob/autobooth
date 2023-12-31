import random
import time
from pprint import pprint
import traceback as tb

from . services.presence import PresenceClient
from . services.camera import CameraClient
from . services.display import DisplayClient
from . services.speech import SpeechClient
from . services.transcribe import TranscribeClient
from . dialog import PhotoboothDialog
from . imagegen import generate_composite, warmup
from . data import get_data_path
from . delay import DelayedTask

listening_path = get_data_path("audio", "listening.mp3")
not_listening_path = get_data_path("audio", "not_listening.mp3")

presence_service = PresenceClient()
camera_service = CameraClient()
display_service = DisplayClient()
speech_service = SpeechClient()
transcribe_service = TranscribeClient()

def get_people_count():
    return 1
    return presence_service("get_person_count", None)

def speak(text, voice_model):
    print(f"speaking with voice model {voice_model}...")
    return speech_service("speak", (text, voice_model))

def transcribe():
    print("transcribing...")
    #speech_service("play_sound", listening_path)
    resp = transcribe_service("transcribe", (None, None))
    #speech_service("play_sound", not_listening_path)
    return resp

def capture():
    print("capturing...")
    return camera_service("capture", None)

def display_image(img_fn):
    print("displaying image...")
    return display_service("display_image", img_fn)

def clear_display():
    display_image('/nfs/photobooth/data/plain-black-background.jpg')

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
        speak(result.message, dialog.voice_model)
        if result.waiting_on == "ready":
            clear_display()
            transcribe()
            img_fn = capture()
            user_message = "ready"
        else:
            user_message = transcribe()
        print(user_message)

def loop():
    print("loop()")
    clear_display()
    flash_warmup = DelayedTask(30 * 60, capture)
    flash_warmup.start()
    people_count = 0
    while people_count <= 0:
        time.sleep(1)
        people_count = get_people_count()
    flash_warmup.cancel()
    run_dialog(people_count=people_count)

def run():
    while True:
        try:
            loop()
        except KeyboardInterrupt:
            break
        except:
            tb.print_exc()

if __name__ == "__main__":
    run()
