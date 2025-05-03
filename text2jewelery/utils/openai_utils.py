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
    print(f"Uploaded image URL: {url}")
    response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
            {
                "role": "system",
                "content": (
                    "You are a jewelry design assistant. Describe this image for downstream geometry parsing. "
                    "Be literal and structured in your language. Describe materials, shape, style, gem placement, and unique features."
                )
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Please describe this jewelry item:"},
                    {"type": "image_url", "image_url": {"url": url}}
                ]
            }
        ]
    )
    print(response.choices[0].message.content)
    
    return response.choices[0].message.content

def create_geometry_from_design(design, error_message=None, description = "") -> str:
    error = f"Previous attempt failed. Error:\n```\n{error_message}\n```" if error_message else ''
    geometry_prompt =  f"""
You are a 3D jewelry designer generating **Python code for Blender 4.3+** using the `bpy` API.

Your task is to construct a physically plausible ring design based on the following structured design description:

**User Description**:  
"{description}"

**Design Breakdown**:
- Base shape: `{design['base_shape']}`
- Material: `{design['material']}` (apply using the **Principled BSDF** node)
- Profile: `{design.get('profile')}`
- Gems: `{json.dumps(design.get('gems', {}))}`
- Engravings: `{json.dumps(design.get('engravings', {}))}`
- Experimental: `{design.get('experimental') or 'none'}`

---
BASE CODE FOR THE RING IN THE CORRECT POSITION (ONLY ADAPT SHAPE AND MATERIALS):
import bpy

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

def create_material(name, color, metallic=1.0, roughness=0.3):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
    return mat

def create_ring_band():
    clear_scene()

    outer_radius = 1.0     # Outer edge of ring
    thickness = 0.2        # Band thickness

    # Create torus in upright orientation (XY ring plane)
    bpy.ops.mesh.primitive_torus_add(
        major_radius=outer_radius - thickness,  # Inner radius
        minor_radius=thickness,
        location=(0, 0, -outer_radius),         # Shift downward so top edge = origin
        rotation=(1.5708, 0, 0)                 # Rotate upright
    )
    ring = bpy.context.active_object
    ring.name = "GoldRing"

    gold = create_material("Gold", (1.0, 0.85, 0.3))
    ring.data.materials.append(gold)

create_ring_band()

---

### Instructions

1. **Clear the scene completely** before modeling.
2. Build geometry that reflects correct real-world **ring proportions**. For example:
   - Ring outer radius: ~1.0 units
   - ENSURE THE RING IS NOT FLAT ON THE XY AXIS! THE BORDER OF THE RING SHOULD BE AT THE ORIGIN (0,0,0) SO THE TRINKET AND STONES CAN BE NICELY PLACED ON TOP OF IT.
   - THE RING SHOULD BE IN THE XZ PLANE! OFFSET THE RING
   - ENSURE THE GEMS ARE PLACED ON TOP OF THE RING. DO NOT OFFSET THE Y-AXIS. THE RING IS ON THE XZ PLANE -> GEMS SHOULD BE CLOSE TO THE ORIGIN OR IF OFFSET; ON THE X AXIS AND POTENTIALLY OFFSET DOWNWARDS
   - Band thickness: ~0.2 units
   - Gem size: ~0.1–0.2 units in radius
   - Use centered origin for modeling

3. Apply materials using only safe Principled BSDF inputs (Blender 4.3):

Valid:
- Base Color
- Metallic
- Roughness
- Alpha
- Emission (only if present)

Do **NOT** use these deprecated or invalid inputs:
- `'Specular'`
- `'Transmission'`
- `'Transmission Roughness'`
- `'Transmission Ratio'`
- `'Emission'` (if node not available — verify it exists first)

4. When assigning materials:
   - Check that the **Principled BSDF** node is present before setting any inputs.
   - Do **not** assume every input exists — use `.get("Principled BSDF")` and check presence of each socket (e.g., `'Emission'`).

5. When setting `rotation_mode`, only use valid enum values:
`'XYZ'`, `'QUATERNION'`, `'AXIS_ANGLE'`  
Do **not** use: `'AXIS_AXIS'` → this will raise an enum error
DO NOT COMMENT THE CODE! DO NOT ADD ANY EXPLANATIONS INLINE! ONLY ADD EXPLANATIONS WITH '//' IN SINGE LINE COMMENTS!
---

### Error Context (from previous run)

{error}

---

###  Output Constraints

- Output **must be valid Python code**, executable in Blender 4.3+
- Do **not** include markdown, triple backticks, or explanations
- Return a clean, standalone `.py` function block (no footer, no render logic)

"""
    response = client.chat.completions.create(
        model="gpt-4.1",
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

def regenerate_geometry_code(
    original_design_text: str,
    rendered_image_file,
    current_code: str
) -> str:
    """
    Refines geometry code based on design prompt and rendered image result.
    Uploads image to Supabase, sends structured prompt to GPT-4o.
    """
    safe_filename = f"{uuid.uuid4().hex}_{os.path.basename(rendered_image_file.name)}"

    image_url = upload_to_supabase(
        rendered_image_file.read(),
        safe_filename
    )

    # Prepare the prompt
    prompt = f"""
You are a Blender assistant.

The user originally described their design like this:

\"\"\"{original_design_text}\"\"\"

You previously generated the following geometry code:

'''python
{current_code}
The resulting image (attached via URL) does not fully match the intended design.
---
IF IT IS NOT A RING, DO NOT USE THE BASE CODE FOR THE RING IN THE CORRECT POSITION (ONLY ADAPT SHAPE AND MATERIALS) AND JUST GENERATE THE REST OF THE GEOMETRY.
BASE CODE FOR THE RING IN THE CORRECT POSITION (ONLY ADAPT SHAPE AND MATERIALS):

import bpy

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

def create_material(name, color, metallic=1.0, roughness=0.3):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
    return mat

def create_ring_band():
    clear_scene()

    outer_radius = 1.0     # Outer edge of ring
    thickness = 0.2        # Band thickness

    # Create torus in upright orientation (XY ring plane)
    bpy.ops.mesh.primitive_torus_add(
        major_radius=outer_radius - thickness,  # Inner radius
        minor_radius=thickness,
        location=(0, 0, -outer_radius),         # Shift downward so top edge = origin
        rotation=(1.5708, 0, 0)                 # Rotate upright
    )
    ring = bpy.context.active_object
    ring.name = "GoldRing"

    gold = create_material("Gold", (1.0, 0.85, 0.3))
    ring.data.materials.append(gold)

create_ring_band()

---

### Instructions

1. **Clear the scene completely** before modeling.
2. Build geometry that reflects correct real-world **ring proportions**. For example:
   - Ring outer radius: ~1.0 units
   - ENSURE THE RING IS NOT FLAT ON THE XY AXIS! THE BORDER OF THE RING SHOULD BE AT THE ORIGIN (0,0,0) SO THE TRINKET AND STONES CAN BE NICELY PLACED ON TOP OF IT.
   - THE RING SHOULD BE IN THE XZ PLANE! OFFSET THE RING
   - ENSURE THE GEMS ARE PLACED ON TOP OF THE RING. DO NOT OFFSET THE Y-AXIS. THE RING IS ON THE XZ PLANE -> GEMS SHOULD BE CLOSE TO THE ORIGIN OR IF OFFSET; ON THE X AXIS AND POTENTIALLY OFFSET DOWNWARDS
   - Band thickness: ~0.2 units
   - Gem size: ~0.1–0.2 units in radius
   - Use centered origin for modeling

3. Apply materials using only safe Principled BSDF inputs (Blender 4.3):

 Valid:
- Base Color
- Metallic
- Roughness
- Alpha
- Emission (only if present)

 Do **NOT** use these deprecated or invalid inputs:
- `'Specular'`
- `'Transmission'`
- `'Transmission Roughness'`
- `'Transmission Ratio'`
- `'Emission'` (if node not available — verify it exists first)

4. When assigning materials:
   - Check that the **Principled BSDF** node is present before setting any inputs.
   - Do **not** assume every input exists — use `.get("Principled BSDF")` and check presence of each socket (e.g., `'Emission'`).

5. When setting `rotation_mode`, only use valid enum values:
 `'XYZ'`, `'QUATERNION'`, `'AXIS_ANGLE'`  
 Do **not** use: `'AXIS_AXIS'` → this will raise an enum error

DO NOT COMMENT THE CODE! DO NOT ADD ANY EXPLANATIONS INLINE! ONLY ADD EXPLANATIONS WITH '//' IN SINGE LINE COMMENTS!
 Please refine the geometry code only to better match the user's intent.
 Do NOT include rendering or export logic.
 Output must be a single, valid Blender Python code block that replaces the geometry section.
"""
   # Send to GPT
    response = client.chat.completions.create(
    model="gpt-4.1",
    messages=[
        {"role": "system", "content": "You improve Blender geometry code. Output only Python."},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
        }
    ]
)

    # Clean and wrap code
    blender_code = response.choices[0].message.content
    cleaned_code = clean_code_block(blender_code)
    footer_code = Path("render_and_export_footer.py").read_text()
    guarded_code = wrap_in_try_block(cleaned_code + "\n\n" + footer_code)

    # Write to file
    script_path = Path("./dynamic_geometry.py")
    script_path.write_text(guarded_code)

    return script_path