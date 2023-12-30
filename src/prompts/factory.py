import random
from jinja2 import Environment, BaseLoader

Prompts = {}

PROMPT_TEMPLATE = """
{{ preamble.text }}

For inspiration, here are some random words: {{ random_words }}

{% for step in steps %}
{{ loop.index }}. {{ step.title }}
Example

(from user): {{ step.user_message.json() }}
(from assistant): {{ step.assistant_message.json() }}

{% endfor %}
"""

word_file = "/usr/share/dict/words"
WORDS = open(word_file).read().splitlines()

def get_random_words(n_words=10):
    words = [random.choice(WORDS) for _ in range(n_words)]
    words = ', '.join(words)
    return words

def render_prompt(prompt):
    template = Environment(loader=BaseLoader).from_string(PROMPT_TEMPLATE)
    random_words = get_random_words()
    return template.render(preamble=prompt.preamble, steps=prompt.steps, random_words=random_words)

def add_prompt(prompt):
    global Prompts
    #Prompts[prompt.name] = render_prompt(prompt)
    Prompts[prompt.name] = prompt
