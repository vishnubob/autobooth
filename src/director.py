import random
import time

from . import chat
from . import prompts
from . services.presence import PresenceClient
from . services.camera import CameraClient
from . services.display import DisplayClient
from . services.speech import SpeechClient
from . services.transcribe import TranscribeClient

presence_service = PresenceClient()
camera_service = CameraClient()
display_service = DisplayClient()
speech_service = SpeechClient()
transcribe_service = TranscribeClient()

def get_person_count():
    return presence_service("get_person_count", None)

def speak(text):
    return speech_service("speak", text)

def transcribe():
    return transcribe_service("transcribe", None)

def capture():
    return camera_service("capture", None)

def display_image(img_fn):
    return display_service("display_image", img_fn)

def run_dialog(person_count=None):
    prompt_list = prompts.list_prompts()
    mode = random.choice(prompt_list)
    mode = 'banter'
    prompt = prompts.get_prompt(mode)

    messages = [
        {"role": "system", "content": prompt},
        {"role": "system", "content": f"{person_count} participants are present"},
    ]

    while True:
        result = chat.photobooth_dialog(messages)
        response = result['choices'][0]['message']
        messages.append(response)
        if 'function_call' in response:
            #bg_model = GenerateBackground.from_response(result)
            #bg = bg_model()
            #display(bg)
            img_fn = capture()
            display_image(img_fn)
            messages.append({'role': 'system', 'content': 'Picture taken and image generated'})
        else:
            msg = response['content']
            print(msg)
            speak(msg)
            response = transcribe()
            messages.append({'role': 'user', 'content': response})


def run():
    while True:
        print("loop")
        person_count = get_person_count()
        if person_count > 0:
            run_dialog(person_count=person_count)
        else:
            time.sleep(1)

if __name__ == "__main__":
    run()
