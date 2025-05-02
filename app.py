import streamlit as st
from db import init_db, get_cached, cache_tags
from scraper import scrape_tiktok
import openai
import subprocess

# --- Initialization ---
init_db()
openai.api_key = st.secrets["OPENAI_API_KEY"]

st.title("Trend-Aware Brand Video Generator")

platform = st.selectbox("Platform", ["TikTok"])  # extend later
if st.button("Fetch Trends"):
    tags = get_cached(platform)
    if not tags:
        tags = scrape_tiktok()
        cache_tags(platform, tags)
    st.session_state.tags = tags

tags = st.session_state.get("tags", [])
trend = st.selectbox("Choose Trend", tags)
brand = st.text_input("Brand / Product")
tone = st.selectbox("Tone", ["Funny", "Serious", "Inspirational"])

if st.button("Generate Video"):
    # 1. Draft script
    prompt = (f"Create a 5-scene, 15-second {platform} script using trend '{trend}'. "
              f"Brand: {brand}. Tone: {tone}.")
    resp = openai.ChatCompletion.create(model="gpt-4o-mini",
                                        messages=[{"role":"user","content":prompt}])
    script = resp.choices[0].message.content
    st.markdown("**Story Script:**")
    st.write(script)

    # 2. Call FFmpeg (template-based)
    # Here we assume a helper that converts script->JSON spec->renders video
    subprocess.run(["python", "render.py", "--script", script, "--output", "out.mp4"])
    st.video("out.mp4")
    st.success("Video generated! Download from sidebar.")
