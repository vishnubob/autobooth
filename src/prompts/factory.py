import json
from jinja2 import Environment, BaseLoader

Prompts = {}

PROMPT_TEMPLATE = """
{{ preamble.text }}

{% for step in steps %}
{{ loop.index }}. {{ step.title }}
Example

(from user): {{ step.user_message.to_json() }}
(from assistant): {{ step.assistant_message.to_json() }}

{% endfor %}
"""

# Class Definitions
class Preamble:
    def __init__(self, text):
        text = ' '.join([it for it in text.split('\n') if it.strip()])
        self.text = text

class GenerateBackground:
    def __init__(self, scene_name=None, prompt=None):
        self.scene_name = scene_name
        self.prompt = prompt

    def to_json(self):
        return json.dumps({
            "scene_name": self.scene_name,
            "prompt": self.prompt
        })

class AssistantMessage:
    def __init__(self, message, continue_session=True, generate_background=None):
        self.message = message
        self.continue_session = continue_session
        self.generate_background = generate_background

    def to_json(self):
        generate_background = self.generate_background.to_json() if self.generate_background else None
        return json.dumps({
            "message": self.message,
            "continue_session": self.continue_session,
            "generate_background": generate_background,
        })

class UserMessage:
    def __init__(self, message, people_count):
        self.message = message
        self.people_count = people_count

    def to_json(self):
        return json.dumps({
            "message": self.message,
            "people_count": self.people_count
        })

class Step:
    def __init__(self, title, user_message, assistant_message):
        self.title = title
        self.user_message = user_message
        self.assistant_message = assistant_message

class Prompt:
    def __init__(self, name, preamble, steps):
        self.name = name
        self.preamble = preamble
        self.steps = steps

    def render(self):
        template = Environment(loader=BaseLoader).from_string(PROMPT_TEMPLATE)
        return template.render(preamble=self.preamble, steps=self.steps)

def add_prompt(prompt):
    global Prompts
    Prompts[prompt.name] = prompt.render()
