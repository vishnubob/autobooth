import os
from redis import Redis
from rq import Worker
import speech_recognition as sr

def get_microphone_index():
    matches = [(idx, nm) for (idx, nm) in enumerate(sr.Microphone.list_microphone_names()) if 'USB' in nm]
    return matches[0][0]

def get_energy_threshold(sample_rate=44100, microphone_index=None):
    if microphone_index is None:
        microphone_index = get_microphone_index()
    with sr.Microphone(device_index=microphone_index, sample_rate=sample_rate) as source:
        rec = sr.Recognizer()
        rec.adjust_for_ambient_noise(source)
        return rec.energy_threshold

def listen(sample_rate=44100, energy_threshold=None, microphone_index=None):
    if microphone_index is None:
        microphone_index = get_microphone_index()
    with sr.Microphone(device_index=microphone_index, sample_rate=sample_rate) as source:
        recognizer = sr.Recognizer()
        if energy_threshold is None:
            recognizer.adjust_for_ambient_noise(source)
        else:
            recognizer.energy_threshold = energy_threshold
        audio = recognizer.listen(source)

    folder = "./audio"
    filename = "microphone-results"
    audio_file_path = f"{folder}/{filename}.wav"

    if not os.path.exists(folder):
        os.mkdir(folder)
    
    with open(audio_file_path, "wb") as f:
        f.write(audio.get_wav_data())

    return os.path.abspath(audio_file_path)
