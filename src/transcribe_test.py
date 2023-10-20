from . services.transcribe import TranscribeClient

cli = TranscribeClient()
text = cli('transcribe', None)
print(text)
