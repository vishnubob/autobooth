#from . import banter
#from . import troll
#from . import standard
#from . import props
from . import dynamic
from . factory import Prompts, render_prompt
from . persona import get_random_persona, get_voice_model

def build_prompt():
    persona = get_random_persona()
    prompt = render_prompt(persona=persona)
    voice_model = get_voice_model(persona.gender)

    return {
        'persona': persona,
        'prompt': prompt,
        'voice_model': voice_model
    }
