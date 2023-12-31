import os
import time
from openai import OpenAI
from . service import Service, ServiceClient

class SpeechService(Service):
    ServiceName = "speech"

class SpeechClient(ServiceClient):
    ServiceName = "speech"
    DefaultTimeout = 1000 * 60 * 2
    
#def play_mp3(fn):
    #cmd = f'mpg123 {fn}'
    #os.system(cmd)

def play_sound(audio_fn: str) -> bool:
    from pygame import mixer
    mixer.init()
    mixer.music.load(audio_fn)
    mixer.music.play()
    while mixer.music.get_busy():
        time.sleep(.1)

    return True

#def do_speak(text=None, model_name='en-US-Neural2-H', language_code='en-US'):
def do_speak(text=None, model_name='en-US-Neural2-A', language_code='en-US'):
    client = OpenAI()

    response = client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=text
    )

    output_fn = '/tmp/tts.mp3'
    response.stream_to_file(output_fn)
    play_sound(output_fn)

#def do_speak(text=None, model_name='en-US-Neural2-H', language_code='en-US'):
def _do_speak(text=None, model_name='en-US-Neural2-A', language_code='en-US'):
    from google.cloud import texttospeech as tts

    client = tts.TextToSpeechClient()
    synthesis_input = tts.SynthesisInput(text=text)

    voice = tts.VoiceSelectionParams(
        name=model_name,
        language_code=language_code
    )

    audio_config = tts.AudioConfig(
        audio_encoding=tts.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    output_fn = '/tmp/tts.mp3'
    with open(output_fn, "wb") as out:
        out.write(response.audio_content)
    play_sound(output_fn)

def speak(text: str) -> bool:
    do_speak(text)
    return True

def start_service():
    service = SpeechService()
    service.start(register_rpc=(speak, play_sound))

if __name__ == "__main__":
    start_service()
