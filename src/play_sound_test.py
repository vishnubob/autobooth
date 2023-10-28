from . services.speech import SpeechClient
from . data import get_data_path
import time

listening_path = get_data_path("audio", "listening.mp3")
not_listening_path = get_data_path("audio", "not_listening.mp3")

cli = SpeechClient()
cli("play_sound", listening_path)
time.sleep(1)
cli("play_sound", not_listening_path)
