from jinja2 import Environment, BaseLoader
from persona import get_random_persona

Prompts = {}

PROMPT_TEMPLATE = """
{{ preamble.text }}

When creating the scenarios, writing the dialog, and interacting with the participants, adopt this persona:

{{ persona.json() }}

In order to coordinate the technical operation of the Photo Booth, you will
exchange a well formed JSON dictionary with the backend software.  Here is an
example of this JSON flow.  It's critical that you adhere to this JSON format.

{% for step in steps %}
{{ loop.index }}. {{ step.title }}
Example

(from user): {{ step.user_message.json() }}
(from assistant): {{ step.assistant_message.json() }}

{% endfor %}
"""

def render_prompt(prompt='dynamic', persona=None):
    template = Environment(loader=BaseLoader).from_string(PROMPT_TEMPLATE)
    persona = persona or get_random_persona()
    return template.render(preamble=prompt.preamble, steps=prompt.steps, persona=persona)

def add_prompt(prompt):
    global Prompts
    Prompts[prompt.name] = render_prompt(prompt)
