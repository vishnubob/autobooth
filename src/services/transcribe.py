import math
import time
import alsaaudio
import numpy as np
import threading
import aubio
import pydub
import os
import tempfile
import shutil
import queue
import multiprocessing as mp
from collections import deque
from openai import OpenAI

from . service import Service, ServiceClient

openai_client = OpenAI()

DEFAULT_SAMPLE_RATE = 44100
DEFAULT_CHANNELS = 1
DEFAULT_FORMAT = alsaaudio.PCM_FORMAT_FLOAT_LE
DEFAULT_DEVICE = 'default'
DEFAULT_CAPTURE_LEVEL = .9
DEFAULT_FRAMES_PER_CHUNK = 2048
DEFAULT_PITCH_RANGE = [85, 255]
DEFAULT_SPEECH_TIMEOUT = 1
DEFAULT_ABSOLUTE_TIMEOUT = 10
DEFAULT_SILENCE_LEVEL_DB = -40

class Timer:
    def __init__(self, timeout=None):
        self.timeout = timeout
        self.reset()

    def reset(self):
        self._timestamp = time.time()

    @property
    def duration(self):
        return time.time() - self._timestamp
    
    @property
    def is_expired(self):
        return self.duration >= self.timeout

class TempWavFile:
    def __init__(
        self,
        sample_rate=DEFAULT_SAMPLE_RATE,
        num_channels=DEFAULT_CHANNELS, 
        normalized=True,
        keep=False
    ):
        self.tempdir = tempfile.mkdtemp()
        self.sample_rate = sample_rate
        self.num_channels = num_channels
        self.normalized = normalized
        self.keep = keep
        (fd, self.file_path) = tempfile.mkstemp(dir=self.tempdir, suffix='.wav')
        os.close(fd)

    def write(self, audio):
        if self.normalized:
            audio = audio * 2 ** 15
        audio = np.int16(audio)[np.newaxis, ...]
        segment = pydub.AudioSegment(
            audio.tobytes(),
            frame_rate=self.sample_rate,
            sample_width=2,
            channels=self.num_channels
        )
        segment.export(self.file_path, format='wav')
        return self.file_path
    
    def __del__(self):
        if not self.keep:
            shutil.rmtree(self.tempdir)

class AudioSource:
    def __init__(
        self,
        sample_rate=DEFAULT_SAMPLE_RATE,
        channels=DEFAULT_CHANNELS,
        format=DEFAULT_FORMAT,
        device=DEFAULT_DEVICE,
        capture_level=DEFAULT_CAPTURE_LEVEL,
        frames_per_chunk=DEFAULT_FRAMES_PER_CHUNK
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.format = format
        self.device = device
        self.frames_per_chunk = frames_per_chunk
        self.record_buffer = None
        self.capture_level = capture_level
        self.open()
        self.set_capture_level()
        self.record_buffer = RecordBuffer(
            source=self.source,
            frames_per_chunk=self.frames_per_chunk,
        )
        self.record_buffer.start()

    def open(self):
        self.source = alsaaudio.PCM(
            alsaaudio.PCM_CAPTURE,
            channels=self.channels,
            rate=self.sample_rate,
            format=self.format,
            device=self.device,
        )

    def close(self):
        if self.record_buffer is not None:
            self.record_buffer.stop()
        self.source = None

    def __del__(self):
        if self.source is not None:
            self.close()

    def set_capture_level(self, channel=alsaaudio.MIXER_CHANNEL_ALL):
        level = self.capture_level
        if level < 1:
            level = int(round(level * 100))
        for mixer_name in alsaaudio.mixers(device=self.device):
            mixer = alsaaudio.Mixer(mixer_name, device=self.device)
            mixer.setvolume(level, channel)

class RecordBuffer(threading.Thread):
    def __init__(self, source=None, frames_per_chunk=None, max_frames=32):
        super().__init__()
        self.daemon = True
        self.frames_per_chunk = frames_per_chunk
        self.source = source
        self.source_info = source.info()
        self._deque = deque(maxlen=max_frames)
        self._running = False
        self._deque_cv = threading.Condition()

    def run(self):
        self._running = True
        self.loop()
    
    def stop(self):
        self._running = False
        self.join()

    def loop(self):
        buffer = b''
        num_bytes = self.frames_per_chunk * 4
        while self._running:
            (sample_len, sample_data) = self.source.read()
            if sample_len == 0:
                continue
            buffer += sample_data
            if len(buffer) >= num_bytes:
                frame_data = buffer[:num_bytes]
                buffer = buffer[num_bytes:]
                chunk = np.frombuffer(frame_data, dtype=aubio.float_type)
                with self._deque_cv:
                    self._deque.append(chunk)
                    self._deque_cv.notify()

    def get(self):
        with self._deque_cv:
            try:
                value = self._deque.popleft()
            except IndexError:
                self._deque_cv.wait()
                value = self._deque.popleft()
            return value
    
    def flush(self):
        self._deque.clear()

class MovingAverage:
    def __init__(self, n_samples=10):
        self.n_samples = n_samples
        init_itr = (0 for _ in range(self.n_samples))
        self._deque = deque(init_itr, maxlen=self.n_samples)

    def __call__(self, value):
        self._deque.append(value)
        return sum(self._deque) / self.n_samples

class TranscribeAudioSource:
    def __init__(
        self,
        audio_source=None,
        silence_level=DEFAULT_SILENCE_LEVEL_DB,
        pitch_range=DEFAULT_PITCH_RANGE,
        speech_timeout=DEFAULT_SPEECH_TIMEOUT,
        absolute_timeout=DEFAULT_ABSOLUTE_TIMEOUT
    ):
        self.audio_source = audio_source
        self.speech_timeout = speech_timeout
        self.absolute_timeout = absolute_timeout
        self.record_buffer = audio_source.record_buffer
        self.silence_level = silence_level
        self.pitch_range = pitch_range
        self.pitcher = aubio.pitch(
            "yin",
            self.audio_source.frames_per_chunk * 2,
            self.audio_source.frames_per_chunk,
            self.audio_source.sample_rate
        )
        self.pitcher.set_unit("Hz")
        self.pitcher.set_silence(self.silence_level)

    def transcribe(self, speech_timeout=None, absolute_timeout=None):
        speech_timeout = speech_timeout or 2
        absolute_timeout = absolute_timeout or 10
        self.record_buffer.flush()
        buffer = None
        wav_file = TempWavFile()
        speech_detected = False
        n_samples = int(round(.15 / (self.record_buffer.frames_per_chunk / self.audio_source.sample_rate)))
        mva = MovingAverage(n_samples=n_samples)
        speech_timer = Timer(timeout=speech_timeout or self.speech_timeout)
        absolute_timer = Timer(timeout=absolute_timeout or self.absolute_timeout)
        while True:
            if absolute_timer.is_expired:
                print('absolute timer expired')
                break
            frames = self.record_buffer.get()
            pitch = self.pitcher(frames)[0]
            if buffer is None:
                buffer = frames
            else:
                buffer = np.concatenate((buffer, frames))
            if speech_detected:
                if pitch > self.pitch_range[0] and pitch < self.pitch_range[1]:
                    speech_timer.reset()
            else:
                if pitch > self.pitch_range[0] and pitch < self.pitch_range[1]:
                    avg_pitch = mva(pitch)
                else:
                    avg_pitch = mva(0)
                if avg_pitch > self.pitch_range[0] and avg_pitch < self.pitch_range[1]:
                    print('speech detected')
                    speech_detected = True
                    speech_timer.reset()
                continue
            if speech_timer.is_expired:
                break
        if speech_detected:
            wav_path = wav_file.write(buffer)
            transcript = self.transcribe_audio(wav_path).strip()
            return transcript

    def transcribe_audio(self, audio_path):
        audio_file = open(audio_path, 'rb')
        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text",
            language='en'
        )
        return transcript

class TranscribeEngine(mp.Process):
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.running = False
        self.command_queue = mp.Queue()
        self.output_queue = mp.Queue()

    def run(self):
        audio_source = AudioSource()
        transcriber = TranscribeAudioSource(audio_source)
        self.running = True
        while self.running:
            item = self.command_queue.get()
            if item[0] == 'transcribe':
                text = transcriber.transcribe(*item[1:])
                self.output_queue.put(text)
            else:
                raise ValueError(item[0])

command_queue = None
output_queue = None

class TranscribeService(Service):
    ServiceName = "transcribe"

class TranscribeClient(ServiceClient):
    ServiceName = "transcribe"
    DefaultTimeout = 1000 * 60 * 2
    
def transcribe(timeouts: tuple[int | None, int | None] = (None, None)) -> str:
    global command_queue, output_queue
    print('transcribing')
    command_queue.put(('transcribe', timeouts[0], timeouts[1]))
    return output_queue.get()

def start_service():
    global command_queue, output_queue
    engine = TranscribeEngine()
    command_queue = engine.command_queue
    output_queue = engine.output_queue
    engine.start()
    service = TranscribeService()
    service.start(register_rpc=(transcribe, ))

if __name__ == "__main__":
    start_service()
