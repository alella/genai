import os
import time
from diffusers import DiffusionPipeline, AutoPipelineForText2Image
from huggingface_hub import login
from core.clients.ollama_client import OllamaClient
from core.bots import MattermostBot
from core.utils import xml_to_json
import requests
from openai import OpenAI


api_llama = OllamaClient("llama3.1")


api_token = os.environ.get("HUGGINGFACE_API_KEY")
os.environ["HUGGINGFACE_HUB_TOKEN"] = api_token
login(token=api_token)
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

nemo = MattermostBot(
    "nemo",
    api_llama,
    "5mmmj6tp17bxjpdftugeh6rjqy",
    max_message_count=3,
    system_prompt="You are a master in generating prompts for text-to-image models. You are an expert in illustrations and art.",
    api_type="ollama",
)


def post_image(file_path, desc):
    channel_id = "358udwdorpf1ipjkhh7ro7qdua"
    with open(file_path, "rb") as file_content:
        file_data = nemo.driver.files.upload_file(
            channel_id, files={"files": (os.path.basename(file_path), file_content)}
        )
        file_id = file_data["file_infos"][0]["id"]
        nemo.driver.posts.create_post(
            {
                "channel_id": channel_id,
                "message": desc,
                "file_ids": [file_id],
            }
        )


def pipe_stable_diffusion_xl(prompt, image_name, **kwargs):
    pipe = DiffusionPipeline.from_pretrained("stabilityai/stable-diffusion-xl-base-1.0")
    pipe.to("mps")
    default_kwargs = {
        "width": 1024,
        "height": 1024,
        "num_inference_steps": 50,
        "num_images_per_prompt": 1,
    }
    default_kwargs.update(kwargs)
    print(default_kwargs)
    result = pipe(prompt, **default_kwargs)
    result.images[0].save(image_name)


def pipe_stable_diffusion_v5(prompt, image_name, **kwargs):
    pipe = DiffusionPipeline.from_pretrained("runwayml/stable-diffusion-v1-5")
    pipe.to("mps")
    default_kwargs = {
        "width": 512,
        "height": 512,
        "num_inference_steps": 100,
        "num_images_per_prompt": 1,
    }
    default_kwargs.update(kwargs)
    print(default_kwargs)
    result = pipe(prompt, **default_kwargs)
    result.images[0].save(image_name)


def pipe_amused512(prompt, image_name, **kwargs):
    pipe = DiffusionPipeline.from_pretrained("amused/amused-512")  # good
    pipe.to("mps")
    default_kwargs = {
        "width": 512,
        "height": 512,
        "num_inference_steps": 500,
        "num_images_per_prompt": 1,
        "guidance_scale": 7,
    }
    default_kwargs.update(kwargs)
    print(default_kwargs)
    result = pipe(prompt, **default_kwargs)
    result.images[0].save(image_name)


def pipe_dalle3(prompt, image_name, **kwargs):
    client = OpenAI()

    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )

    image_url = response.data[0].url
    print(image_url)
    # Download url
    image_data = requests.get(image_url).content
    with open(image_name, "wb") as f:
        f.write(image_data)


def pipe_dalle2(prompt, image_name, **kwargs):
    client = OpenAI()

    response = client.images.generate(
        model="dall-e-2",
        prompt=prompt,
        size="512x512",
        quality="standard",
        n=1,
    )

    image_url = response.data[0].url
    print(image_url)
    # Download url
    image_data = requests.get(image_url).content
    with open(image_name, "wb") as f:
        f.write(image_data)


def generate_and_post_image(prompt, model_id):
    negative_prompt = "ugly, messy, bad, mushroom"
    start_time = time.time()
    image_name = f"output.png"
    model_functions[model_id](prompt, image_name, negative_prompt=negative_prompt)
    end_time = time.time()
    execution_time_minutes = (end_time - start_time) / 60
    desc = f"**Prompt:** {prompt}\n **model**: `{model_id}`\n **Execution Time:** {execution_time_minutes:.2f} minutes"
    post_image(image_name, desc)


model_functions = {
    "stabilityai/stable-diffusion-xl-base-1.0": pipe_stable_diffusion_xl,
    "amused/amused-512": pipe_amused512,
    "runwayml/stable-diffusion-v1-5": pipe_stable_diffusion_v5,
    "dall-e-3": pipe_dalle3,
    "dall-e-2": pipe_dalle2,
}

import random

prompts = []
for i in range(100):
    style = random.choice(
        [
            "cartoon",
            "painted illustration",
            "sketch",
            "chibi",
            "ghilbi",
            "drawing",
            "digital art",
            "vector art",
            "soft washed 3d style",
        ]
    )
    palette = random.choice(
        [
            "Vintage Hardware",
            "Retro Future",
            "Soft Focus",
            "Muted Earth Tones",
            "Neon Noir",
            "Watercolor Whimsy",
            "Cinematic Monochrome",
            "Digital Dreamscapes",
            "Rustic Charm",
            "Graffiti Street Art",
        ]
    )
    no_char = random.choice(
        ["Images need not have characters.", "Images need not have characters.", ""]
    )
    nemo.reset("")
    resp = nemo.invoke(
        "",
        f"""Generate a prompt using the following rules for text-to-image LLM. The output should be raw text in <prompt> xml tag.

    1. Add specific details and rich descriptions to create a more vivid and immersive scene. Include one unique style (example: {style}) and a color pallet (example: {palette}).
    2. Organize the information logically, presenting the main subject first (make the subject pop), followed by actions, settings, and additional contextual details. Ensure the flow creates a coherent and complete picture.
    3. Reinforce important visual elements by repeating key descriptors and emphasizing contrasts or unique features.
    4. Incorporate extra descriptive layers that enhance depth and evoke emotions or concepts, such as feelings, atmospheres, or thematic elements.
    5. Keep the prompts simple, minimalistic and pleasant. Do not mention numbers.
    6. Use a max of 50 words.
    7. Avoid mushrooms and mermaids. {no_char}
    """,
    )
    data = xml_to_json(resp["raw_content"])
    if "prompt" not in data:
        continue
    prompt = data["prompt"]
    print(prompt)
    prompts.append(prompt)


for i, prompt in enumerate(prompts):
    generate_and_post_image(prompt, "amused/amused-512")
    generate_and_post_image(prompt, "runwayml/stable-diffusion-v1-5")
    time.sleep(600)
