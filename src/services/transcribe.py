import os
import multiprocessing as mp
import speech_recognition as sr
from openai import OpenAI

client = OpenAI()
from . service import Service, ServiceClient

energy_threshold = None
microphone_index = None

def transcribe_audio(audio_file_path=None, model_name='whisper-1'):
    with open(audio_file_path, "rb") as fh:
        response = client.audio.transcriptions.create(model=model_name, file=fh, language='en')
    return response.text
    #return response["text"]

def get_microphone_index(device="USB"):
    matches = [(idx, nm) for (idx, nm) in enumerate(sr.Microphone.list_microphone_names()) if device in nm]
    return matches[0][0]

def get_energy_threshold(sample_rate=44100, microphone_index=None):
    if microphone_index is None:
        microphone_index = get_microphone_index()
    #with sr.Microphone(device_index=microphone_index, sample_rate=sample_rate) as source:
    #with sr.Microphone(device_index=microphone_index) as source:
    #with sr.Microphone(device_index=microphone_index, sample_rate=sample_rate, chunk_size=512) as source:
    with sr.Microphone() as source:
        rec = sr.Recognizer()
        rec.adjust_for_ambient_noise(source)
    return rec.energy_threshold

def listen(sample_rate=44100, chunk_size=1024, energy_threshold=None, microphone_index=None):
    if microphone_index is None:
        microphone_index = get_microphone_index()
    #with sr.Microphone() as source:
    #with sr.Microphone(device_index=microphone_index) as source:
    #with sr.Microphone(device_index=microphone_index, sample_rate=sample_rate, chunk_size=chunk_size) as source:
    with sr.Microphone() as source:
        recognizer = sr.Recognizer()
        if energy_threshold is None:
            recognizer.adjust_for_ambient_noise(source)
        else:
            recognizer.energy_threshold = energy_threshold
        try:
            audio = recognizer.listen(source, timeout=10)
        except:
            return None

    folder = "./audio"
    filename = "microphone-results"
    audio_file_path = f"{folder}/{filename}.wav"

    if not os.path.exists(folder):
        os.mkdir(folder)
    
    with open(audio_file_path, "wb") as f:
        f.write(audio.get_wav_data())

    return os.path.abspath(audio_file_path)

class TranscribeService(Service):
    ServiceName = "transcribe"

class TranscribeClient(ServiceClient):
    ServiceName = "transcribe"
    DefaultTimeout = 1000 * 60 * 2

def transcribe() -> str:
    global energy_threshold, microphone_index
    audio_path = listen(energy_threshold=energy_threshold, microphone_index=microphone_index)
    if not audio_path:
        return ''
    return transcribe_audio(audio_path)

def calibrate() -> int:
    global energy_threshold, microphone_index
    energy_threshold = get_energy_threshold(microphone_index=microphone_index)
    return energy_threshold

def start_service():
    global energy_threshold, microphone_index
    microphone_index = get_microphone_index()
    energy_threshold = get_energy_threshold(microphone_index=microphone_index)
    print(microphone_index, energy_threshold)
    service = TranscribeService()
    service.start(register_rpc=(transcribe, calibrate))

if __name__ == "__main__":
    start_service()
