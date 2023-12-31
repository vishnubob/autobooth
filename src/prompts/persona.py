import os
import json
import random
from models import Persona

rootdir, _ = os.path.split(os.path.abspath(__file__))

GenderVoiceMap = {
    'male': ['Alloy', 'Echo', 'Fable', 'Onyx'],
    'female': ['Nova', 'Shimmer']
}

def get_voice_model(gender):
    voice_models = GenderVoiceMap[gender.lower()]
    return random.choice(voice_models)

def load_personas():
    persona_jsfn = os.path.join(rootdir, 'persona.json')
    with open(persona_jsfn) as fh:
        persona_list = json.load(fh)
    persona_models = [Persona(**per) for per in persona_list]
    return persona_models

PersonaList = load_personas()

def get_random_persona():
    global PersonaList
    return random.choice(PersonaList)
