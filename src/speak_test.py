from . services.speech import SpeechClient

cli = SpeechClient()
cli('speak', 'hello world')
