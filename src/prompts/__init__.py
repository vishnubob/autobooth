from . import precise
#from . import banter
#from . import troll
#from . import standard
#from . import props
from . factory import Prompts, render_prompt

def list_prompts():
    return list(Prompts.keys())

def get_prompt(name):
    prompt = Prompts[name]
    prompt = render_prompt(prompt)
    print(prompt)
    return prompt
