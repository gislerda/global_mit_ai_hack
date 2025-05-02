# solar-detective

# 1. environment
python -m venv .venv && source .venv/bin/activate
pip install sqlmodel requests beautifulsoup4 pdfplumber folium gradio \
            langchain duckduckgo_search openai

export OPENAI_API_KEY=sk‑…

# 2. pull data
python solar_detective.py ingest          # adds MNRE + SECI projects

# 3. explore
python solar_detective.py dashboard