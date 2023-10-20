from redis import Redis
from rq import SimpleWorker, Queue
import random
import time
import jobs
import prompts
import chat

def wait_on(job, poll=1):
    while True:
        job.refresh()
        if job.result is not None:
            return
        time.sleep(poll)

def call(func, *args, **kw):
    job = queue.enqueue(func, *args, **kw)
    wait_on(job)
    return job.return_value()

def transcribe():
    audio_file_path = call(
        jobs.listen.listen, 
        energy_threshold=energy_threshold,
        microphone_index=microphone_index
    )
    text = call(jobs.transcribe.transcribe, audio_file_path=audio_file_path)
    return text

def run_dialog():
    prompt_list = prompts.list_prompts()
    mode = random.choice(prompt_list)
    mode = 'banter'
    prompt = prompts.get_prompt(mode)
    count = random.choice(['one', 'two', 'three', 'four', 'five', 'six'])

    messages = [
        {"role": "system", "content": prompt},
        {"role": "system", "content": f"{count} participants are present"},
    ]

    while True:
        result = chat.photobooth_dialog(messages)
        response = result['choices'][0]['message']
        messages.append(response)
        if 'function_call' in response:
            #bg_model = GenerateBackground.from_response(result)
            #bg = bg_model()
            #display(bg)
            messages.append({'role': 'system', 'content': 'Picture taken and image generated'})
        else:
            msg = response['content']
            print(msg)
            jobs.speak.speak(response['content'])
            response = transcribe()
            messages.append({'role': 'user', 'content': response})

queue = Queue(connection=Redis())
microphone_index = call(jobs.listen.get_microphone_index)
energy_threshold = call(jobs.listen.get_energy_threshold)
run_dialog()
