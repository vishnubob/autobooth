import os
import glob

prompt_dir = os.path.split(os.path.abspath(__file__))[0]
pattern = os.path.join(prompt_dir, '*.txt')
prompt_files = glob.glob(pattern)
prompt_map = {}
for fn in prompt_files:
    name = os.path.split(fn)[-1].split('.')[0]
    with open(fn) as fh:
        prompt_map[name] = fh.read()

def list_prompts():
    global prompt_map
    return list(prompt_map.keys())

def get_prompt(name):
    global prompt_map
    return prompt_map[name]
