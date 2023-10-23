from . import banter
from . import troll
from . import standard
from . factory import Prompts

def list_prompts():
    return list(Prompts.keys())

def get_prompt(name):
    return Prompts[name]
