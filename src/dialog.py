import random
from openai import OpenAI
from pprint import pprint

client = OpenAI()
from . prompts.models import *
from . prompts import build_prompt

class PhotoboothDialog:
    def __init__(self, prompt_info=None):
        self.prompt_info = prompt_info or build_prompt()
        print(self.prompt_info['prompt'])
        self.messages = [{"role": "system", "content": self.prompt_info['prompt']}]

    @property
    def voice_model(self):
        return self.prompt_info['voice_model']

    def parse_completion(self, completion):
        response = completion.choices[0].message
        pprint(response)
        self.messages.append(response)
        return AssistantMessage.parse_raw(response.content)

    def generate_response(self):
        #model="gpt-3.5-turbo-0613",
        #model="gpt-4-0613"
        model = "gpt-4-1106-preview"
        completion = client.chat.completions.create(
            model=model,
            temperature=1.0,
            messages=self.messages
        )
        return completion

    def get_response(self, people_count=None, message=None):
        user_message = UserMessage(people_count=people_count, message=message)
        self.messages.append({"role": "user", "content": user_message.json()})
        completion = self.generate_response()
        return self.parse_completion(completion)
