import openai
from instructor import OpenAISchema
from pydantic import Field
from typing import List, Any

class GenerateBackground(OpenAISchema):
    "Generate the background image"

    scene_name: str = Field(..., description="The name of the scene")
    prompt: str = Field(..., description="Prompt used to generate the background image")

    def take_picture(self):
        img = Image.open('dua-example.png')
        return img

    def __call__(self):
        pprint(self.prompt)
        #img = self.take_picture()
        #img_nobg = remove(img, alpha_matting=True)
        result = openai.Image.create(prompt=self.prompt, n=1, size="1024x1024")
        image_url = result['data'][0]['url']
        bg_image = download_image_to_pil(image_url)
        bg_image = bg_image.convert('RGBA')
        fg_image = Image.open('duo-2-mask.png')
        return Image.alpha_composite(fg_image, bg_image)
        result = openai.Image.create_edit(
            image=open("duo-2-mask.png", "rb"),
            prompt=self.prompt,
            n=1,
            size="1024x1024"
        )
        image_url = result['data'][0]['url']
        return download_image_to_pil(image_url)

func_desc = {
    'description': 'Generate the background image',
    'name': 'GenerateBackground',
    'parameters': {
        'properties': {
            'prompt': {
                'description': 'Prompt used to generate the background image', 'type': 'string'},
                'scene_name': {'description': 'The name of the scene', 'type': 'string'}},
    'required': ['prompt', 'scene_name'],
    'type': 'object'}
}


def photobooth_dialog(messages):
    completion = openai.ChatCompletion.create(
        model="gpt-4-0613",
        temperature=1.0,
        functions=[func_desc],
        messages=messages,
    )
    return completion

