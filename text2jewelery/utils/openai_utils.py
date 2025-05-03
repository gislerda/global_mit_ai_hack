from pydantic import BaseModel
from typing import Optional, Dict
from openai import OpenAI
from openai import OpenAI
from dotenv import load_dotenv
import os

from supabase import create_client
import uuid
from pathlib import Path

dotenv_path = "../.env"
load_dotenv(dotenv_path)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_BUCKET = "mit-hack"


client = OpenAI(api_key=OPENAI_API_KEY)


supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_to_supabase(file_bytes: bytes, filename: str) -> str:
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    res = supabase.storage.from_(SUPABASE_BUCKET).upload(
        unique_name,
        file_bytes,
        {"content-type": "image/png"}  # or jpg etc.
    )


    return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{unique_name}"


class RingDesignIntent(BaseModel):
    base_shape: str
    material: str
    profile: str

    gems: Optional[Dict[str, Dict[str, str]]] = None
    engravings: Optional[Dict[str, Dict[str, str]]] = None
    experimental: Optional[str] = None

def parse_user_intent(prompt: str) -> dict:
    response = client.responses.parse(
        model="gpt-4o",
        input=[
            {"role": "system", "content": (
                "Extract structured ring design. Use dictionaries for 'gems' and 'engravings'. "
                "Each gem should have type, position, cut, size. Each engraving should have text, location, and style."
            )},
            {"role": "user", "content": prompt}
        ],
        text_format=RingDesignIntent
    )
    return response.output_parsed

class ImageDescription(BaseModel):
    description: str

def describe_reference_image(uploaded_file) -> str:
    """
    Use GPT-4o to describe the uploaded reference image.
    Returns a descriptive string (or parsed output).
    """
    url = upload_to_supabase(uploaded_file.read(), uploaded_file.name)

    response = client.responses.parse(
        model="gpt-4o",
        input=[
            {
                "role": "system",
                "content": (
                    "You are a jewelry design assistant. "
                    "Describe the ring or jewelry piece shown in the image as clearly as possible. "
                    "Focus on materials, shapes, stone placement, symmetry, and stylistic elements."
                )
            },
            {
                "role": "user",
                "content":  url
                    
                
            }
        ],
        text_format=ImageDescription
    )

    return response.output_parsed.description