import streamlit as st
import json
import subprocess
import uuid
from pathlib import Path
import streamlit_3d as sd
from utils.openai_utils import parse_user_intent, describe_reference_image, create_geometry_from_design
import base64

st.set_page_config(layout='wide')

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

# Layout columns
col1, col2 = st.columns([1, 2])

# Left: chat, upload, and buttons
with col1:
    st.subheader("Describe Initial Design")
    init_prompt = st.text_area("Prompt", "A classic gold ring with a diamond on top", height=100)


    uploaded_file = st.file_uploader("Upload a reference image (optional)", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        st.image(uploaded_file, caption="Uploaded Reference", use_container_width=True)

    if st.button("Describe Image with AI"):
        desc = describe_reference_image(uploaded_file)
        st.session_state["image_description"] = desc
        st.markdown("### 🧠 AI-Generated Description")
        st.info(desc)
    
    if st.button("Generate Design"):
        parsed_intent = parse_user_intent(init_prompt)
        st.session_state.design_state.update(parsed_intent)
        st.success("Design parsed and updated from prompt.")

    if st.button("Generate Render & Model"):
        out_dir = Path("blender_output")
        out_dir.mkdir(exist_ok=True)

        # Optional: save the JSON design intent (for trace/debugging)
        design_file = out_dir / f"design_{uuid.uuid4().hex}.json"
        with open(design_file, "w") as f:
            json.dump(st.session_state.design_state, f)

        # Get image description (if available)
        image_description = st.session_state.get("image_description", "")

        # 🔧 Generate Blender geometry script
        
        
        MAX_RETRIES = 2
        retries = 0
        success = False

        while retries <= MAX_RETRIES and not success:
            script_path = create_geometry_from_design(st.session_state.design_state, error_message=None if retries == 0 else last_error)

            result = subprocess.run([
                "blender", "--background", "--python", str(script_path)
            ], capture_output=True, text=True)
            print("Return code:", result.returncode)
            print("STDOUT:")
            print(result.stdout)
            print("STDERR:")
            print(result.stderr)
            if result.returncode == 0:
                success = True
            else:
                last_error = result.stderr.strip()
                retries += 1
        print(success)
        st.success("Render & model generation complete.")

# Right: base shape grid and modifications
with col2:
    st.subheader("Select a Base Shape")
    shape_labels = ["ring", "earring", "necklace", "piercing"]
    shape_files = {
        "ring": "base_shape/ring.glb",
        "earring": "base_shape/earring.glb",
        "necklace": "base_shape/necklace.glb",
        "piercing": "base_shape/piercing.glb"
    }

    selected_shape = st.radio("Base Shape", shape_labels, index=shape_labels.index(st.session_state.design_state["base"]))
    st.session_state.design_state["base"] = selected_shape

    preview_cols = st.columns(2)
    for i, label in enumerate(shape_labels):
        with preview_cols[i % 2]:
            st.markdown(f"**{label.capitalize()}**")
            model_path = shape_files[label].replace("\\", "/")
            sd.streamlit_3d(model=model_path, height=200)

    st.subheader("Add Step-by-Step Modification")
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
