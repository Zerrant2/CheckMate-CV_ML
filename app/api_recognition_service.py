import base64
from openai import OpenAI
import os
from dotenv import load_dotenv

def api_recognition(image_path):
    #Read image and conver to base64

    with open(image_path, "rb") as f:
        image_bytes = f.read()
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    image_data_url = f"data:image/jpeg;base64,{image_base64}"

    #Client
    load_dotenv()
    API_KEY = os.getenv("OPENROUTER_API")
    MODEL_NAME = os.getenv("OPENROUTER_MODEL")
    prompt_file = os.getenv("SYSTEM_PROMPT")
    with open(prompt_file, "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read()
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=API_KEY,
    )

    #Prepare and api
    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"{SYSTEM_PROMPT}"},
                    {"type": "image_url", "image_url": {"url": image_data_url}}
                ]
            }
        ]
    )
    return completion.choices[0].message.content


def api_recognition_document(text):
    #Read image and conver to base64

    #Client
    load_dotenv()
    API_KEY = os.getenv("OPENROUTER_API")
    MODEL_NAME = os.getenv("OPENROUTER_MODEL")
    prompt_file = os.getenv("DOCUMENT_PROMPT")
    with open(prompt_file, "r", encoding="utf-8") as f:
        DOCUMENT_PROMPT = f.read()

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=API_KEY,
    )

    #Prepare and api
    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"{DOCUMENT_PROMPT}, {text}"}
                ]
            }
        ]
    )
    return completion.choices[0].message.content
