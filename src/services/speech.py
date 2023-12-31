import os
import time
from openai import OpenAI
from . service import Service, ServiceClient

class SpeechService(Service):
    ServiceName = "speech"

class SpeechClient(ServiceClient):
    ServiceName = "speech"
    DefaultTimeout = 1000 * 60 * 2
    
def play_sound(audio_fn: str) -> bool:
    from pygame import mixer
    mixer.init()
    mixer.music.load(audio_fn)
    mixer.music.play()
    while mixer.music.get_busy():
        time.sleep(.1)

    return True

def do_speak(text=None, model_name='alloy'):
    client = OpenAI()

    response = client.audio.speech.create(
        model="tts-1",
        voice=model_name,
        input=text
    )

    output_fn = '/tmp/tts.mp3'
    response.stream_to_file(output_fn)
    play_sound(output_fn)

def speak(text_model: tuple[str, str]) -> bool:
    do_speak(*text_model)
    return True

def start_service():
    service = SpeechService()
    service.start(register_rpc=(speak, play_sound))

if __name__ == "__main__":
    start_service()
