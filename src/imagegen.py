import os
import replicate
import requests
from PIL import Image
from io import BytesIO
import numpy as np
from tempfile import TemporaryDirectory
from pathlib import Path
from skimage.filters import threshold_otsu

def crop_and_scale_image(image, size):
    current_width, current_height = image.size
    current_aspect_ratio = current_width / current_height
    new_width, new_height = size
    new_aspect_ratio = new_width / new_height

    if current_aspect_ratio == new_aspect_ratio:
        return image.resize(size, Image.Resampling.LANCZOS)

    if current_aspect_ratio > new_aspect_ratio:
        crop_width = int(current_height * new_aspect_ratio)
        crop_height = current_height
    else:
        crop_width = current_width
        crop_height = int(current_width / new_aspect_ratio)

    left = (current_width - crop_width) // 2
    top = (current_height - crop_height) // 2
    right = (current_width + crop_width) // 2
    bottom = (current_height + crop_height) // 2
    cropped_image = image.crop((left, top, right, bottom))
    return cropped_image.resize(size, Image.Resampling.LANCZOS)

def download_image_to_pil(url):
    try:
        response = requests.get(url)
        # Check if the request was successful (status code 200)
        response.raise_for_status()
        # Open image from binary data and return as PIL Image object
        return Image.open(BytesIO(response.content))
    except requests.RequestException as e:
        print(f"Error during request: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

def generate_image_controlnet(prompt, num_inference_steps=20, **kw):
    print("Generating new background")
    #model = 'lucataco/sdxl-controlnet:06d6fae3b75ab68a28cd2900afa6033166910dd09fd9751047043a5bbb4c184b'
    model = "vishnubob/controlnet"
    kw['prompt'] = prompt
    kw['num_inference_steps'] = num_inference_steps
    deployment = replicate.deployments.get(model)
    prediction = deployment.predictions.create(input=kw)
    prediction.wait()
    img = download_image_to_pil(prediction.output)
    return img

def remove_background(**kw):
    print("Removing background")
    #model = "ilkerc/rembg:e809cddc666ccfd38a044f795cf65baab62eedc4273d096bf05935b9a3059b59"
    #url = replicate.run(model, input=kw)
    model = "vishnubob/rembg"
    kw['alpha_matting'] = True
    deployment = replicate.deployments.get(model)
    prediction = deployment.predictions.create(input=kw)
    prediction.wait()
    img = download_image_to_pil(prediction.output)
    return img

"""
def generate_image_controlnet(prompt, num_inference_steps=20, **kw):
    print("Generating new background")
    model = 'lucataco/sdxl-controlnet:06d6fae3b75ab68a28cd2900afa6033166910dd09fd9751047043a5bbb4c184b'
    kw['prompt'] = prompt
    kw['num_inference_steps'] = num_inference_steps
    url = replicate.run(model, input=kw)
    img = download_image_to_pil(url)
    return img

def remove_background(**kw):
    print("Removing background")
    model = "ilkerc/rembg:e809cddc666ccfd38a044f795cf65baab62eedc4273d096bf05935b9a3059b59"
    kw['alpha_matting'] = True
    url = replicate.run(model, input=kw)
    img = download_image_to_pil(url)
    return img
"""

def generate_composite(img_fn, prompt, rotate=180):
    (path, ext) = img_fn.split('.')
    target_fn = f'{path}-composite.{ext}'
    fg_img = Image.open(img_fn)
    if rotate:
        fg_img = fg_img.rotate(rotate)

    resolution = (1344, 768)
    fg_img = crop_and_scale_image(fg_img, resolution)
    with TemporaryDirectory() as root:
        fg_img_path = Path(root, 'fg_img.png')
        fg_img.save(str(fg_img_path), format="png")
        fg_img_nobg = remove_background(image=fg_img_path)

    #rembg_session = new_session('u2net_human_seg')
    #print('remove')
    #fg_img_nobg = remove(
        #fg_img,
        #matte=True,
        #session=rembg_session
    #)
    fg_mask = np.array(fg_img_nobg, dtype=np.uint8)
    fg_mask = np.squeeze(fg_mask[..., -1])
    thresh = threshold_otsu(fg_mask)
    fg_mask = (fg_mask < thresh).astype(np.uint8) * 0xFF
    fg_mask = Image.fromarray(fg_mask, mode='L').convert('RGB')

    style = '35mm photograph, film, professional, 4k, highly detailed, HDR'
    bg_negative_prompt = 'drawing, painting, crayon, sketch, graphite, impressionist, noisy, blurry, soft, deformed, ugly, person, people, text'
    prompt = f'{prompt} {style}'

    with TemporaryDirectory() as root:
        fg_img_path = Path(root, 'fg_img.png')
        fg_img_nobg.save(str(fg_img_path), format="png")
        bg_img = generate_image_controlnet(prompt, negative_prompt=bg_negative_prompt, image=fg_img_path)

    comp_img = Image.alpha_composite(bg_img.convert('RGBA'), fg_img_nobg.convert('RGBA'))
    comp_img = comp_img.convert('RGB')
    comp_img.save(target_fn)
    print(f"Returning composite at {target_fn}")
    return target_fn

def warmup():
    img = Image.new('RGB', (512, 512))
    img.save('/tmp/warmup.png')
    warmup = generate_composite('/tmp/warmup.png', 'nothing')
    os.unlink(warmup)

if __name__ == "__main__":
    img_fn = "/nfs/photobooth/captures/capture_Oct21-2023_23-51-59.jpg"
    prompt = "colorful cinematic photo of a snow capped mountain range."
    generate_composite(img_fn, prompt)
