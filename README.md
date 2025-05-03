# 💍 AI-Powered 3D Jewelry Designer

This project enables users to design and generate 3D jewelry—starting with rings—using natural language input, AI reasoning, and Blender scripting.

## 🚀 Features

- Prompt-to-3D: Describe your ring, and AI generates the Blender geometry.
- Image input: Upload a reference photo and let AI describe and interpret it.
- Supports rings, earrings, necklaces, and piercings.
- GPT-4o-powered reasoning and geometry generation (via OpenAI API).
- Streamlit interface with live 3D previews and downloadable outputs.
- Iterative REPL-like refinement loop to improve geometry based on render.

## 📁 Project Structure

```
text2jewelry/
├── streamlit_designer.py         # Main Streamlit UI entry point
├── openai_utils.py               # OpenAI helper functions (parsing, generation)
├── base_shapes.py                # Predefined primitive geometry builders
├── render_from_state.py          # Script to render from JSON design
├── render_and_export_footer.py   # Shared render/export code for Blender scripts
├── blender_output/               # Final GLB and PNG outputs
├── base_shape/                   # Base GLB shapes for preview (ring.glb, etc)
└── utils/                        # Utility modules
```

## ⚙️ Setup

### Requirements

- Python 3.10+
- Blender 4.3+ installed and available in PATH
- FFmpeg (optional for video postprocessing)
- OpenAI Python SDK (`openai`)
- Supabase client (`supabase-py`)
- Streamlit, Pydantic, etc.

### Installation

```bash
git clone https://github.com/your-username/ai-jewelry-designer.git
cd ai-jewelry-designer/text2jewelry

python -m venv .venv
.venv\Scripts\activate  # On Windows
pip install -r requirements.txt
```

### Run

```bash
streamlit run streamlit_designer.py
```

### Environment Variables

Set the following in a `.env` or directly in your shell:

- `OPENAI_API_KEY=sk-...`
- `SUPABASE_URL=https://...`
- `SUPABASE_KEY=...`
- `SUPABASE_BUCKET=mit-hack`

## 🧠 AI Usage

- GPT-4o is used for:
  - Extracting structured intent from user prompt
  - Refining geometry based on render feedback
  - Generating Blender Python scripts

- Image understanding uses `chat.completions` with image URLs from Supabase.

## 📦 Outputs

- `.glb`: Exported 3D model
- `.png`: Rendered image preview

## 🛠 Dev Tips

- Modify `render_and_export_footer.py` for render settings
- Use the "Regenerate / Refine" button for AI-driven corrections

## 📜 License

MIT License © 2025
