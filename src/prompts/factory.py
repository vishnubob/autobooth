from jinja2 import Environment, BaseLoader

Prompts = {}

PROMPT_TEMPLATE = """
{{ preamble.text }}

{% for step in steps %}
{{ loop.index }}. {{ step.title }}
Example

(from user): {{ step.user_message.json() }}
(from assistant): {{ step.assistant_message.json() }}

{% endfor %}
"""

def render_prompt(prompt):
    template = Environment(loader=BaseLoader).from_string(PROMPT_TEMPLATE)
    return template.render(preamble=prompt.preamble, steps=prompt.steps)

def add_prompt(prompt):
    global Prompts
    Prompts[prompt.name] = render_prompt(prompt)
