import random
import time
from pprint import pprint
import traceback as tb
import sys

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

presence_service = PresenceClient()
camera_service = CameraClient()
display_service = DisplayClient()
speech_service = SpeechClient()
transcribe_service = TranscribeClient()

def get_people_count():
    #return 1
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

def display_text(text):
    print("displaying text...")
    return display_service("display_text", text)

def clear_display():
    display_image('/nfs/photobooth/data/plain-black-background.jpg')

def run_dialog(people_count=None):
    dialog = PhotoboothDialog()

    user_message = None
    while True:
        people_count = get_people_count()
        result = dialog.get_response(people_count=people_count, message=user_message)
        pprint(result)
        if result.generate_background: 
            #img_fn = capture()
            prompt = result.generate_background.prompt
            comp_fn = generate_composite(img_fn, prompt)
            display_image(comp_fn)
        speak(result.message, dialog.voice_model)
        if not result.continue_session:
            print("Result closed session")
            break
        #if people_count == 0:
            #print("No people")
            #break
        if result.waiting_on == "ready":
            clear_display()
            transcribe()
            img_fn = capture()
            user_message = "ready"
            display_text('Please wait...')
        else:
            user_message = transcribe()
        print(user_message)

def loop():
    sys.stdout.flush()
    print("loop()")
    clear_display()
    #flash_warmup = DelayedTask(30 * 60, capture)
    #flash_warmup.start()
    people_count = 0
    while people_count <= 0:
        time.sleep(1)
        people_count = get_people_count()
    #flash_warmup.cancel()
    run_dialog(people_count=people_count)
    # cool down
    time.sleep(5)

def run():
    while True:
        try:
            loop()
        except KeyboardInterrupt:
            break
        except:
            tb.print_exc()
            speak("Sorry, the photobooth software crashed.  Resetting.", "echo")
            time.sleep(5)

if __name__ == "__main__":
    run()
