from pydantic import BaseModel
from typing import Optional, Dict
from openai import OpenAI
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
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

def create_geometry_from_design(design, error_message=None) -> str:
    error = f"Previous attempt failed. Error:\n```\n{error_message}\n```" if error_message else ''
    geometry_prompt =  f"""
You are a 3D jewelry designer generating Python code for Blender 4.3+.

Use only the `bpy` Python API to:
- Clear the scene fully
- Create a ring with base shape: {design['base_shape']}
- Use material: {design['material']}, built using the new **Principled BSDF** node
- Avoid deprecated or invalid BSDF inputs such as:
  ❌ 'Specular'
  ❌ 'Transmission'
  ❌ 'Transmission Roughness'
  ❌ 'Transmission Ratio'

✅ Use only compatible BSDF inputs in Blender 4.3, such as:
  - Base Color
  - Metallic
  - Roughness
  - Alpha
  - Emission (optional for glow)

Add design elements:
- Gems: {json.dumps(design.get('gems', {}))}
- Profile: {design.get('profile')}
- Engravings: {json.dumps(design.get('engravings', {}))}
- Experimental details: {design.get('experimental') or 'none'}
⚠️ Use only valid inputs for the Principled BSDF in Blender 4.3. Avoid: 'Transmission', 'Specular', 'Transmission Roughness', 'Transmission Ratio'

{error}

Return ONLY valid executable Python code (no markdown).
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You're a geometry code generator for Blender. Output a single .py script."},
            {"role": "user", "content": geometry_prompt}
        ]
    )
    blender_code = response.choices[0].message.content
    cleaned_code = clean_code_block(blender_code)
    footer_code = Path(r"./render_and_export_footer.py").read_text()
    guarded_code = wrap_in_try_block(cleaned_code + "\n\n" + footer_code)
    code_path = Path(r"./dynamic_geometry.py")
    code_path.write_text(guarded_code)
    return code_path

def clean_code_block(text: str) -> str:
    if text.startswith("```python"):
        text = text.removeprefix("```python").strip()
    elif text.startswith("```"):
        text = text.removeprefix("```").strip()
    if text.endswith("```"):
        text = text.removesuffix("```").strip()
    return text

def wrap_in_try_block(code: str) -> str:
    return (
        "import sys\nimport traceback\n\n"
        "try:\n"
        + "\n".join(f"    {line}" for line in code.splitlines())
        + "\nexcept Exception as e:\n"
        "    traceback.print_exc()\n"
        "    sys.exit(1)\n"
    )