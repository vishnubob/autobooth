from pydantic import BaseModel, Field
from typing import Optional, List

# Preamble model
class Preamble(BaseModel):
    text: str

    def __init__(self, text: str):
        super().__init__(text=' '.join([it for it in text.split('\n') if it.strip()]))

# GenerateBackground model
class GenerateBackground(BaseModel):
    scene_name: Optional[str] = Field(None)
    prompt: Optional[str] = Field(None)

# AssistantMessage model
class AssistantMessage(BaseModel):
    message: str
    continue_session: bool = Field(True)
    waiting_on: Optional[str] = Field(None)
    generate_background: Optional[GenerateBackground] = Field(None)

# SystemMessage
class SystemMessage(BaseModel):
    message: Optional[str] = Field(None)

# UserMessage model
class UserMessage(BaseModel):
    message: Optional[str] = Field(None)
    people_count: int

# Step model
class Step(BaseModel):
    title: str
    user_message: UserMessage
    assistant_message: AssistantMessage

class Persona(BaseModel):
    name: str
    age: int
    big_five: List[str]
    myers_briggs: str
    humor_style: str
    disposition: str
    interests: List[str]
    gender: str

# Prompt model
class Prompt(BaseModel):
    name: str
    preamble: Preamble
    steps: List[Step]

    # You'd still need to define your render method and associated logic here, just like in your original class.
    def render(self):
        template = Environment(loader=BaseLoader).from_string(PROMPT_TEMPLATE)
        return template.render(preamble=self.preamble, steps=self.steps)
