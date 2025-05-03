import streamlit as st
import json
import subprocess
import uuid
from pathlib import Path
import streamlit_3d as sd

# State persistence
if "design_state" not in st.session_state:
    st.session_state.design_state = {
        "base": "ring",
        "material": "gold",
        "profile": "rounded",
        "features": []
    }
    st.session_state.history = []

# Helper to save state
def save_state():
    st.session_state.history.append(json.loads(json.dumps(st.session_state.design_state)))

# Header
st.title("💍 AI-Powered Jewelry Designer")
st.markdown("Design a ring step by step with AI + Blender.")

# Base shape selection with 3D preview
st.subheader("1. Select a Base Shape")
base_shape_options = {
    "ring": r"base_shape/ring.glb",
    "earring": r"base_shape/earring.glb",
    "necklace": r"base_shape/necklace.glb",
    "piercing": r"base_shape/piercing.glb"
}
base_shape = st.selectbox("Select a base shape:", list(base_shape_options.keys()))
base_model_path = base_shape_options[base_shape].replace("\\", "/")

st.markdown("#### Preview of selected shape")
#absolute_path = str(Path(__file__).parent / base_model_path)
value = sd.streamlit_3d(model=base_model_path, height=500)
st.write(value)

if base_shape != st.session_state.design_state["base"]:
    st.session_state.design_state["base"] = base_shape
    st.session_state.design_state["features"] = []  # Reset features
    save_state()

# Initial prompt
st.subheader("2. Describe Initial Design")
init_prompt = st.text_input("Describe the initial look of the jewelry:", "A classic gold ring with a diamond on top")
if st.button("Start Design"):
    st.session_state.design_state["material"] = "gold"
    save_state()
    st.success("Design initialized.")

# Add features step-by-step
st.subheader("3. Step-by-step Modifications")
mod_prompt = st.text_input("Add a modification (e.g., 'add a ruby on the side'):")
if st.button("Preview Modification"):
    # Naive NLP parsing stub
    if "diamond" in mod_prompt.lower():
        st.session_state.design_state["features"].append({
            "type": "gem",
            "gem_type": "diamond",
            "cut": "round",
            "position": "top"
        })
        save_state()
        st.success("Diamond added.")
    elif "ruby" in mod_prompt.lower():
        st.session_state.design_state["features"].append({
            "type": "gem",
            "gem_type": "ruby",
            "cut": "oval",
            "position": "side"
        })
        save_state()
        st.success("Ruby added.")
    else:
        st.warning("Unsupported modification (stub NLP). Add 'diamond' or 'ruby'.")

# Show current JSON
st.markdown("### Current Design State")
st.code(json.dumps(st.session_state.design_state, indent=2))

# Export and run Blender
if st.button("Generate Render & Model"):
    # Save to temp JSON
    out_dir = Path("blender_output")
    out_dir.mkdir(exist_ok=True)
    design_file = out_dir / f"design_{uuid.uuid4().hex}.json"
    with open(design_file, "w") as f:
        json.dump(st.session_state.design_state, f)

    # Call Blender
    result = subprocess.run([
        "blender", "--background", "--python", "render_from_state.py", "--", str(design_file)
    ])

    st.success("Render task submitted. Check the Blender output folder.")
