import openai, subprocess, json
from render import render_video

openai.api_key = None  # set by CLI

def draft_script(brand, trend, tone, scenes=5):
    prompt = (
        f"Create a {scenes}-scene, 15-second TikTok script using trend '{trend}'. "
        f"Brand: {brand}. Tone: {tone}. "
        "Return as a JSON list of objects: "
        "[{scene:1, text:'...', duration:3}, ...]"
    )
    resp = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}]
    )
    content = resp.choices[0].message.content
    # assume content is valid JSON
    return json.loads(content)

def generate_video(script_json, audio_file, output="out.mp4"):
    # script_json: list of scenes with 'text' and 'duration'
    render_video(script_json, audio_file, output)
    return output
