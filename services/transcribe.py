import openai

def transcribe(audio_file_path=None, model_name='whisper-1'):
    with open(audio_file_path, "rb") as fh:
        response = openai.Audio.transcribe(model_name, fh)

    return response["text"]
