from google.cloud import texttospeech as tts
from playsound import playsound

def speak(text=None, model_name='en-US-Neural2-H', language_code='en-US'):
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

    output_fn = '/tmp/tts.wav'
    with open(output_fn, "wb") as out:
        out.write(response.audio_content)

    playsound(output_fn)
    return True
