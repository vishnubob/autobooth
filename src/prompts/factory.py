import random
from jinja2 import Environment, BaseLoader
from . persona import get_random_persona

Prompts = {}

PROMPT_TEMPLATE = """
{{ preamble.text }}

When creating the scenarios, writing the dialog, and interacting with the participants, adopt this persona:

{{ persona }}

In order to coordinate the technical operation of the Photo Booth, you will
exchange a well formed JSON dictionary with the backend software.  Here is an
example of this JSON flow.  It's critical that you adhere to this JSON format.

{% for step in steps %}
{{ loop.index }}. {{ step.title }}
Example

(from user): {{ step.user_message.json() }}
(from assistant): {{ step.assistant_message.json() }}

{% endfor %}

Always use 'ready' as the keyword for the participants to indicate when they are ready to have their picture taken.
"""

def render_prompt(prompt_name='dynamic', persona=None):
    global Prompts
    prompt = Prompts[prompt_name]
    template = Environment(loader=BaseLoader).from_string(PROMPT_TEMPLATE)
    persona = persona or get_random_persona()
    steps =  random.choice(prompt.example_sessions)
    return template.render(preamble=prompt.preamble, steps=steps, persona=persona)

def add_prompt(prompt):
    global Prompts
    Prompts[prompt.name] = prompt
